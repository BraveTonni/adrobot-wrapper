"""Сценарии добавления и удаления офферов в потоке кампании."""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import replace

from app.application.catalog.service import Catalog
from app.application.errors import (
    ConflictError,
    NotFoundError,
    RepositoryNotFoundError,
)
from app.application.offer.validation import ensure_offer_exists
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
from app.domain.shares import rebalance_active_offers

logger = logging.getLogger(__name__)


class CampaignEditor:
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

    async def add_offer(
        self,
        campaign_id: int,
        stream_id: int,
        offer_id: int,
        *,
        actor: str = "unknown",
    ) -> Stream:
        return await self._mutate(
            campaign_id,
            stream_id,
            offer_id,
            action="stream.offer_add",
            actor=actor,
            add=True,
        )

    async def remove_offer(
        self,
        campaign_id: int,
        stream_id: int,
        offer_id: int,
        *,
        actor: str = "unknown",
    ) -> Stream:
        return await self._mutate(
            campaign_id,
            stream_id,
            offer_id,
            action="stream.offer_remove",
            actor=actor,
            add=False,
        )

    async def cancel_draft(
        self,
        campaign_id: int,
        stream_id: int,
        *,
        actor: str = "unknown",
    ) -> Stream:
        return await self._draft_mutation(
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

        return await self._draft_mutation(
            campaign_id,
            stream_id,
            action="stream.offer_restore",
            actor=actor,
            change=restore,
        )

    async def push(
        self,
        campaign_id: int,
        stream_id: int,
        *,
        actor: str = "unknown",
    ) -> Stream:
        operation_id = await self._audit.begin(
            action="stream.push",
            actor=actor,
            entity_type="stream",
            entity_id=stream_id,
            campaign_id=campaign_id,
            stream_id=stream_id,
        )
        stream: Stream | None = None
        try:
            stream = await self._load_stream(campaign_id, stream_id)
            try:
                push_offers = offers_for_push(stream.offers)
            except ValueError as exc:
                raise ConflictError(str(exc)) from exc
            updated_remote = await self._repository.update_stream(
                stream_id, push_offers
            )
            if self._drafts is not None:
                await self._drafts.sync_stream(updated_remote)
                updated = await self._drafts.get_stream(campaign_id, stream_id)
            else:
                updated = updated_remote
        except asyncio.CancelledError as exc:
            await asyncio.shield(
                self._finish_safely(
                    operation_id,
                    status="cancelled",
                    campaign_id=campaign_id,
                    stream_id=stream_id,
                    before_payload=(
                        _offers_payload(stream.offers) if stream else None
                    ),
                    error=repr(exc),
                )
            )
            raise
        except Exception as exc:
            await self._finish_safely(
                operation_id,
                status="failed",
                campaign_id=campaign_id,
                stream_id=stream_id,
                before_payload=(
                    _offers_payload(stream.offers) if stream else None
                ),
                error=str(exc),
            )
            raise

        await self._finish_safely(
            operation_id,
            status="ok",
            campaign_id=campaign_id,
            stream_id=stream_id,
            before_payload=_offers_payload(stream.offers),
            after_payload=_offers_payload(updated.offers),
        )
        return updated

    async def _draft_mutation(
        self,
        campaign_id: int,
        stream_id: int,
        *,
        action: str,
        actor: str,
        change: Callable[[list[StreamOffer]], list[StreamOffer]],
        rebalance: bool = True,
    ) -> Stream:
        if self._drafts is None:
            raise ConflictError("черновики потоков недоступны")
        operation_id = await self._audit.begin(
            action=action,
            actor=actor,
            entity_type="stream",
            entity_id=stream_id,
            campaign_id=campaign_id,
            stream_id=stream_id,
        )
        stream: Stream | None = None
        try:
            stream = await self._load_stream(campaign_id, stream_id)
            updated = await self._save_draft(
                stream,
                change(stream.offers),
                rebalance=rebalance,
            )
        except asyncio.CancelledError as exc:
            await asyncio.shield(
                self._finish_safely(
                    operation_id,
                    status="cancelled",
                    campaign_id=campaign_id,
                    stream_id=stream_id,
                    before_payload=(
                        _offers_payload(stream.offers) if stream else None
                    ),
                    error=repr(exc),
                )
            )
            raise
        except Exception as exc:
            await self._finish_safely(
                operation_id,
                status="failed",
                campaign_id=campaign_id,
                stream_id=stream_id,
                before_payload=(
                    _offers_payload(stream.offers) if stream else None
                ),
                error=str(exc),
            )
            raise

        await self._finish_safely(
            operation_id,
            status="ok",
            campaign_id=campaign_id,
            stream_id=stream_id,
            before_payload=_offers_payload(stream.offers),
            after_payload=_offers_payload(updated.offers),
        )
        return updated

    async def _mutate(
        self,
        campaign_id: int,
        stream_id: int,
        offer_id: int,
        *,
        action: str,
        actor: str,
        add: bool,
    ) -> Stream:
        operation_id = await self._audit.begin(
            action=action,
            actor=actor,
            entity_type="stream",
            entity_id=stream_id,
            campaign_id=campaign_id,
            stream_id=stream_id,
            detail={"offer_id": offer_id},
        )
        stream: Stream | None = None
        try:
            if add:
                if self._catalog is None:
                    await ensure_offer_exists(self._repository, offer_id)
                elif not any(
                    offer.id == offer_id
                    for offer in await self._catalog.offers()
                ):
                    raise NotFoundError(
                        f"Оффер #{offer_id} не найден в каталоге Keitaro"
                    )
            stream = await self._load_stream(campaign_id, stream_id)
            if add:
                current = next(
                    (
                        offer
                        for offer in stream.offers
                        if offer.offer_id == offer_id
                    ),
                    None,
                )
                if current is not None and not current.is_deleted:
                    raise ConflictError(f"Оффер #{offer_id} уже есть в потоке")
                if current is not None:
                    offers = restore_soft_deleted_offer(
                        stream.offers, offer_id
                    )
                else:
                    offers = [
                        *stream.offers,
                        StreamOffer(
                            offer_id=offer_id,
                            share=1,
                            state="active",
                            published_share=0,
                            published_state="deleted",
                            draft_share=1,
                            draft_state="active",
                        ),
                    ]
            else:
                current = next(
                    (
                        offer
                        for offer in stream.offers
                        if offer.offer_id == offer_id
                    ),
                    None,
                )
                if current is None or current.is_deleted:
                    raise NotFoundError(
                        f"Оффер #{offer_id} не найден в потоке"
                    )
                if self._drafts is not None:
                    offers = soft_delete_offer(stream.offers, offer_id)
                else:
                    offers = [
                        offer
                        for offer in stream.offers
                        if offer.offer_id != offer_id
                    ]
                if not offers or (
                    self._drafts is None
                    and not [
                        offer
                        for offer in offers
                        if offer.state is None
                        or offer.state.lower() == "active"
                    ]
                ):
                    raise ConflictError(
                        "Нельзя удалить последний оффер: "
                        "сначала добавьте другой"
                    )

            if self._drafts is not None:
                updated = await self._save_draft(stream, offers)
            else:
                updated = await self._save(stream, offers, action=action)
        except asyncio.CancelledError as exc:
            await asyncio.shield(
                self._finish_safely(
                    operation_id,
                    status="cancelled",
                    campaign_id=campaign_id,
                    stream_id=stream_id,
                    before_payload=(
                        _offers_payload(stream.offers) if stream else None
                    ),
                    error=repr(exc),
                )
            )
            raise
        except Exception as exc:
            await self._finish_safely(
                operation_id,
                status="failed",
                campaign_id=campaign_id,
                stream_id=stream_id,
                before_payload=(
                    _offers_payload(stream.offers) if stream else None
                ),
                error=str(exc),
            )
            raise

        await self._finish_safely(
            operation_id,
            status="ok",
            campaign_id=campaign_id,
            stream_id=stream_id,
            before_payload=_offers_payload(stream.offers),
            after_payload=_offers_payload(updated.offers),
        )
        return updated

    async def _load_stream(self, campaign_id: int, stream_id: int) -> Stream:
        try:
            if self._drafts is not None:
                stream = await self._drafts.get_stream(campaign_id, stream_id)
            else:
                stream = await self._repository.get_stream(stream_id)
        except RepositoryNotFoundError as exc:
            raise NotFoundError(f"Поток #{stream_id} не найден") from exc

        if stream.campaign_id != campaign_id:
            raise NotFoundError(
                f"Поток #{stream_id} не принадлежит кампании #{campaign_id}"
            )
        if not stream.uses_offers:
            raise ConflictError(f"Поток «{stream.name}» не редактирует офферы")

        return stream

    async def _save(
        self, stream: Stream, offers: list[StreamOffer], *, action: str
    ) -> Stream:
        try:
            updated_offers = rebalance_active_offers(offers)
            push_offers = offers_for_push(updated_offers)
        except ValueError as exc:
            raise ConflictError(str(exc)) from exc
        updated = await self._repository.update_stream(stream.id, push_offers)

        total = sum(offer.share for offer in updated.offers)
        if updated.offers and total != 100:
            logger.error(
                "Keitaro сохранил доли с неверной суммой",
                extra={
                    "stream_id": stream.id,
                    "total": total,
                    "action": action,
                },
            )

        logger.info(
            "офферы потока обновлены",
            extra={
                "stream_id": stream.id,
                "campaign_id": stream.campaign_id,
                "action": action,
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

    async def _finish_safely(
        self,
        operation_id: int,
        *,
        status: str,
        campaign_id: int,
        stream_id: int,
        before_payload: list[object] | None = None,
        after_payload: list[object] | None = None,
        error: str | None = None,
    ) -> None:
        try:
            await self._audit.finish(
                operation_id,
                status=status,
                campaign_id=campaign_id,
                stream_id=stream_id,
                entity_id=stream_id,
                before_payload=before_payload,
                after_payload=after_payload,
                error=error,
            )
        except Exception as exc:
            logger.error(
                "не удалось завершить запись аудита",
                extra={
                    "operation_id": operation_id,
                    "status": status,
                    "exception_type": type(exc).__name__,
                },
            )


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
