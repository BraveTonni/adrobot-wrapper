"""Сценарии добавления и удаления офферов в потоке кампании."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace

from app.application.catalog.service import Catalog
from app.application.errors import (
    ConflictError,
    NotFoundError,
    RepositoryNotFoundError,
)
from app.application.offer.validation import ensure_offer_in_catalog
from app.application.ports import (
    AuditRepository,
    CampaignEditingRepository,
    CampaignSnapshotRepository,
)
from app.domain.campaigns.entities import Stream, StreamOffer
from app.domain.campaigns.offer_state import (
    cancel_draft as cancel_offer_draft,
)
from app.domain.campaigns.offer_state import (
    offers_for_push,
    soft_delete_offer,
)
from app.domain.campaigns.offer_state import (
    restore_offer as restore_soft_deleted_offer,
)
from app.domain.shares import (
    is_active_offer,
    rebalance_active_offers,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _Attempt:
    """Изменяющая операция: её запись аудита и поток до изменения."""

    operation_id: int
    campaign_id: int
    stream_id: int
    before: Stream | None = None


class CampaignEditor:
    """Редактор офферов потока.

    Без хранилища черновиков каждое изменение сразу публикуется в Keitaro.
    С хранилищем (`drafts`) изменения копятся локально и уходят отдельным
    `push`, который отказывается затирать поток, изменённый в Keitaro.
    """

    def __init__(
        self,
        repository: CampaignEditingRepository,
        audit: AuditRepository,
        catalog: Catalog | None = None,
        drafts: CampaignSnapshotRepository | None = None,
    ) -> None:
        self._repository = repository
        self._audit = audit
        self._catalog = catalog
        self._drafts = drafts

    @property
    def publishes_immediately(self) -> bool:
        """Изменения уходят в Keitaro сразу, а не ждут явной публикации."""
        return self._drafts is None

    async def add_offer(
        self,
        campaign_id: int,
        stream_id: int,
        offer_id: int,
        *,
        actor: str = "unknown",
    ) -> Stream:
        attempt = await self._begin(
            "stream.offer_add",
            actor,
            campaign_id,
            stream_id,
            {"offer_id": offer_id},
        )

        async def run() -> Stream:
            await ensure_offer_in_catalog(
                self._catalog, self._repository, offer_id
            )
            stream = await self._load_stream(campaign_id, stream_id)
            attempt.before = stream
            known = _find(stream.offers, offer_id)
            if known is not None and not known.is_deleted:
                raise ConflictError(f"Оффер #{offer_id} уже есть в потоке")
            offers = (
                restore_soft_deleted_offer(stream.offers, offer_id)
                if known is not None
                else [*stream.offers, _new_offer(offer_id)]
            )
            return await self._publish_change(stream, offers)

        return await self._execute(attempt, run)

    async def remove_offer(
        self,
        campaign_id: int,
        stream_id: int,
        offer_id: int,
        *,
        actor: str = "unknown",
    ) -> Stream:
        attempt = await self._begin(
            "stream.offer_remove",
            actor,
            campaign_id,
            stream_id,
            {"offer_id": offer_id},
        )

        async def run() -> Stream:
            stream = await self._load_stream(campaign_id, stream_id)
            attempt.before = stream
            known = _find(stream.offers, offer_id)
            if known is None or known.is_deleted:
                raise NotFoundError(f"Оффер #{offer_id} не найден в потоке")
            offers = (
                soft_delete_offer(stream.offers, offer_id)
                if self._drafts is not None
                else [
                    item for item in stream.offers if item.offer_id != offer_id
                ]
            )
            if not any(is_active_offer(item) for item in offers):
                raise ConflictError(
                    "Нельзя удалить последний оффер: сначала добавьте другой"
                )
            return await self._publish_change(stream, offers)

        return await self._execute(attempt, run)

    async def cancel_draft(
        self,
        campaign_id: int,
        stream_id: int,
        *,
        actor: str = "unknown",
    ) -> Stream:
        return await self._change_draft(
            campaign_id,
            stream_id,
            action="stream.draft_cancel",
            actor=actor,
            change=cancel_offer_draft,
            rebalance=False,
        )

    async def restore_offer(
        self,
        campaign_id: int,
        stream_id: int,
        offer_id: int,
        *,
        actor: str = "unknown",
    ) -> Stream:
        def restore(offers: list[StreamOffer]) -> list[StreamOffer]:
            try:
                return restore_soft_deleted_offer(offers, offer_id)
            except ValueError as exc:
                raise ConflictError(str(exc)) from exc

        return await self._change_draft(
            campaign_id,
            stream_id,
            action="stream.offer_restore",
            actor=actor,
            change=restore,
            rebalance=True,
        )

    async def push(
        self,
        campaign_id: int,
        stream_id: int,
        *,
        actor: str = "unknown",
    ) -> Stream:
        attempt = await self._begin(
            "stream.push", actor, campaign_id, stream_id
        )

        async def run() -> Stream:
            if self._drafts is None:
                raise ConflictError("черновики потоков недоступны")
            draft = await self._load_stream(campaign_id, stream_id)
            attempt.before = draft
            try:
                push_offers = offers_for_push(draft.offers)
            except ValueError as exc:
                raise ConflictError(str(exc)) from exc
            remote = await self._fetch_remote_stream(stream_id)
            if _published(draft.offers) != _published(remote.offers):
                raise ConflictError(
                    "Поток изменился в Keitaro после загрузки черновика. "
                    "Обновите кампанию и повторите изменения."
                )
            updated = await self._repository.update_stream(
                stream_id, push_offers, current=remote
            )
            await self._drafts.sync_stream(updated)
            return await self._drafts.get_stream(campaign_id, stream_id)

        return await self._execute(attempt, run)

    async def _change_draft(
        self,
        campaign_id: int,
        stream_id: int,
        *,
        action: str,
        actor: str,
        change: Callable[[list[StreamOffer]], list[StreamOffer]],
        rebalance: bool,
    ) -> Stream:
        attempt = await self._begin(action, actor, campaign_id, stream_id)

        async def run() -> Stream:
            if self._drafts is None:
                raise ConflictError("черновики потоков недоступны")
            stream = await self._load_stream(campaign_id, stream_id)
            attempt.before = stream
            return await self._save_draft(
                stream, change(stream.offers), rebalance=rebalance
            )

        return await self._execute(attempt, run)

    async def _begin(
        self,
        action: str,
        actor: str,
        campaign_id: int,
        stream_id: int,
        detail: dict[str, object] | None = None,
    ) -> _Attempt:
        operation_id = await self._audit.begin(
            action=action,
            actor=actor,
            entity_type="stream",
            entity_id=stream_id,
            campaign_id=campaign_id,
            stream_id=stream_id,
            detail=detail,
        )
        return _Attempt(
            operation_id=operation_id,
            campaign_id=campaign_id,
            stream_id=stream_id,
        )

    async def _execute(
        self, attempt: _Attempt, run: Callable[[], Awaitable[Stream]]
    ) -> Stream:
        """Выполняет изменение и закрывает запись аудита с его итогом."""
        try:
            updated = await run()
        except asyncio.CancelledError as exc:
            await asyncio.shield(
                self._finish(attempt, status="cancelled", error=repr(exc))
            )
            raise
        except Exception as exc:
            await self._finish(attempt, status="failed", error=str(exc))
            raise
        await self._finish(attempt, status="ok", after=updated)
        return updated

    async def _finish(
        self,
        attempt: _Attempt,
        *,
        status: str,
        after: Stream | None = None,
        error: str | None = None,
    ) -> None:
        try:
            await self._audit.finish(
                attempt.operation_id,
                status=status,
                campaign_id=attempt.campaign_id,
                stream_id=attempt.stream_id,
                entity_id=attempt.stream_id,
                before_payload=(
                    _offers_payload(attempt.before.offers)
                    if attempt.before is not None
                    else None
                ),
                after_payload=(
                    _offers_payload(after.offers)
                    if after is not None
                    else None
                ),
                error=error,
            )
        except Exception as exc:
            logger.error(
                "не удалось завершить запись аудита",
                extra={
                    "operation_id": attempt.operation_id,
                    "status": status,
                    "exception_type": type(exc).__name__,
                },
            )

    async def _load_stream(self, campaign_id: int, stream_id: int) -> Stream:
        if self._drafts is not None:
            try:
                stream = await self._drafts.get_stream(campaign_id, stream_id)
            except RepositoryNotFoundError as exc:
                raise NotFoundError(f"Поток #{stream_id} не найден") from exc
        else:
            stream = await self._fetch_remote_stream(stream_id)

        if stream.campaign_id != campaign_id:
            raise NotFoundError(
                f"Поток #{stream_id} не принадлежит кампании #{campaign_id}"
            )
        if not stream.uses_offers:
            raise ConflictError(f"Поток «{stream.name}» не редактирует офферы")

        return stream

    async def _fetch_remote_stream(self, stream_id: int) -> Stream:
        try:
            return await self._repository.get_stream(stream_id)
        except RepositoryNotFoundError as exc:
            raise NotFoundError(f"Поток #{stream_id} не найден") from exc

    async def _publish_change(
        self, stream: Stream, offers: list[StreamOffer]
    ) -> Stream:
        if self._drafts is not None:
            return await self._save_draft(stream, offers)

        try:
            rebalanced = rebalance_active_offers(offers)
            push_offers = offers_for_push(rebalanced)
        except ValueError as exc:
            raise ConflictError(str(exc)) from exc
        updated = await self._repository.update_stream(
            stream.id, push_offers, current=stream
        )
        total = sum(offer.share for offer in updated.offers)
        if updated.offers and total != 100:
            logger.error(
                "Keitaro сохранил доли с неверной суммой",
                extra={"stream_id": stream.id, "total": total},
            )
        logger.info(
            "офферы потока обновлены",
            extra={
                "stream_id": stream.id,
                "campaign_id": stream.campaign_id,
                "offer_ids": [offer.offer_id for offer in updated.offers],
                "shares": [offer.share for offer in updated.offers],
            },
        )
        return updated

    async def _save_draft(
        self,
        stream: Stream,
        offers: list[StreamOffer],
        *,
        rebalance: bool = True,
    ) -> Stream:
        if self._drafts is None:
            raise ConflictError("черновики потоков недоступны")
        if rebalance:
            try:
                offers = rebalance_active_offers(offers, require_active=False)
            except ValueError as exc:
                raise ConflictError(str(exc)) from exc
        await self._drafts.save_offers(stream.id, offers)
        return replace(stream, offers=offers)


def _find(offers: list[StreamOffer], offer_id: int) -> StreamOffer | None:
    return next(
        (offer for offer in offers if offer.offer_id == offer_id), None
    )


def _new_offer(offer_id: int) -> StreamOffer:
    """Оффер, добавленный локально и ещё не опубликованный в Keitaro."""
    return StreamOffer(
        offer_id=offer_id,
        share=1,
        state="active",
        published_share=0,
        published_state="deleted",
        draft_share=1,
        draft_state="active",
    )


def _published(
    offers: list[StreamOffer],
) -> dict[int, tuple[int | None, str | None]]:
    """Опубликованные в Keitaro офферы: доля и состояние."""
    return {
        offer.offer_id: (offer.published_share, offer.published_state)
        for offer in offers
        if offer.published_state != "deleted"
    }


def _offers_payload(offers: list[StreamOffer]) -> list[object]:
    return [
        {
            "offer_id": offer.offer_id,
            "share": offer.share,
            "state": offer.state,
            "metadata": offer.metadata,
            "is_pinned": offer.is_pinned,
            "published_state": offer.published_state,
            "published_share": offer.published_share,
            "draft_state": offer.draft_state,
            "draft_share": offer.draft_share,
            "is_deleted": offer.is_deleted,
        }
        for offer in offers
    ]
