"""Сценарии добавления и удаления офферов в потоке кампании."""

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
        self, campaign_id: int, stream_id: int, offer_id: int
    ) -> Stream:
        await ensure_offer_exists(self._repository, offer_id)
        stream = await self._load_stream(campaign_id, stream_id)
        if any(offer.offer_id == offer_id for offer in stream.offers):
            raise ConflictError(f"Оффер #{offer_id} уже есть в потоке")

        offers = [
            *stream.offers,
            StreamOffer(offer_id=offer_id, state="active"),
        ]
        return await self._save(stream, offers, action="stream.offer_add")

    async def remove_offer(
        self, campaign_id: int, stream_id: int, offer_id: int
    ) -> Stream:
        stream = await self._load_stream(campaign_id, stream_id)
        remaining = [
            offer for offer in stream.offers if offer.offer_id != offer_id
        ]
        if len(remaining) == len(stream.offers):
            raise NotFoundError(f"Оффер #{offer_id} не найден в потоке")
        if not remaining:
            raise ConflictError(
                "Нельзя удалить последний оффер: сначала добавьте другой"
            )

        return await self._save(
            stream, remaining, action="stream.offer_remove"
        )

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
        await self._audit.record(
            action=action,
            status="ok",
            campaign_id=stream.campaign_id,
            stream_id=stream.id,
            detail={
                "before": [
                    {"offer_id": offer.offer_id, "share": offer.share}
                    for offer in stream.offers
                ],
                "after": [
                    {"offer_id": offer.offer_id, "share": offer.share}
                    for offer in updated.offers
                ],
            },
        )
        return updated
