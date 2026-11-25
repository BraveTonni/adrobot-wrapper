"""Сценарии добавления и удаления офферов в потоке кампании."""

import asyncio
import logging
from dataclasses import replace

from app.application.errors import (
    ConflictError,
    NotFoundError,
    RepositoryNotFoundError,
)
from app.application.offer.validation import ensure_offer_exists
from app.application.ports import AuditRepository, CampaignEditingRepository
from app.domain.campaigns.entities import Stream, StreamOffer
from app.domain.shares import distribute_shares

logger = logging.getLogger(__name__)


class CampaignEditor:
    def __init__(
        self, repository: CampaignEditingRepository, audit: AuditRepository
    ) -> None:
        self._repository = repository
        self._audit = audit

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
                await ensure_offer_exists(self._repository, offer_id)
            stream = await self._load_stream(campaign_id, stream_id)
            if add:
                if any(offer.offer_id == offer_id for offer in stream.offers):
                    raise ConflictError(f"Оффер #{offer_id} уже есть в потоке")
                offers = [
                    *stream.offers,
                    StreamOffer(offer_id=offer_id, state="active"),
                ]
            else:
                offers = [
                    offer
                    for offer in stream.offers
                    if offer.offer_id != offer_id
                ]
                if len(offers) == len(stream.offers):
                    raise NotFoundError(f"Оффер #{offer_id} не найден в потоке")
                if not offers:
                    raise ConflictError(
                        "Нельзя удалить последний оффер: сначала добавьте другой"
                    )

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
            shares = distribute_shares(len(offers))
        except ValueError as exc:
            raise ConflictError(str(exc)) from exc

        updated_offers = [
            replace(offer, share=share)
            for offer, share in zip(offers, shares, strict=True)
        ]
        updated = await self._repository.update_stream(
            stream.id, updated_offers
        )

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

    async def _finish_safely(
        self,
        operation_id: int,
        *,
        status: str,
        campaign_id: int,
        stream_id: int,
        before_payload: list[dict[str, object]] | None = None,
        after_payload: list[dict[str, object]] | None = None,
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


def _offers_payload(offers: list[StreamOffer]) -> list[dict[str, object]]:
    return [
        {
            "offer_id": offer.offer_id,
            "share": offer.share,
            "state": offer.state,
            "metadata": offer.metadata,
        }
        for offer in offers
    ]
