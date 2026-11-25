"""Редактирование офферов потока существующей кампании.

Каждое изменение - чтение-модификация-запись: поток перечитывается,
затем полный массив offers отправляется целиком с равномерно
пересчитанными долями.
"""

import logging

from app.domain.shares import distribute_shares
from app.keitaro.client import KeitaroClient
from app.keitaro.errors import KeitaroError
from app.keitaro.schemas import Stream, StreamOffer
from app.services.errors import ConflictError, NotFoundError
from app.services.ports import AuditLog

logger = logging.getLogger(__name__)


class CampaignEditor:
    def __init__(self, client: KeitaroClient, audit: AuditLog) -> None:
        self._client = client
        self._audit = audit

    async def add_offer(
        self, campaign_id: int, stream_id: int, offer_id: int
    ) -> Stream:
        await self._check_offer(offer_id)
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
            # Поток без офферов отправляет трафик в никуда.
            raise ConflictError(
                "Нельзя удалить последний оффер: сначала добавьте другой"
            )
        return await self._save(
            stream, remaining, action="stream.offer_remove"
        )

    async def _check_offer(self, offer_id: int) -> None:
        try:
            await self._client.get_offer(offer_id)
        except KeitaroError as exc:
            if exc.status == 404:
                raise NotFoundError(
                    f"Оффер #{offer_id} не найден в Keitaro"
                ) from exc
            raise

    async def _load_stream(self, campaign_id: int, stream_id: int) -> Stream:
        try:
            stream = await self._client.get_stream(stream_id)
        except KeitaroError as exc:
            if exc.status == 404:
                raise NotFoundError(f"Поток #{stream_id} не найден") from exc
            raise
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
        payload = {
            "offers": [
                offer.to_api(share)
                for offer, share in zip(offers, shares, strict=True)
            ]
        }
        updated = await self._client.update_stream(stream.id, payload)

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
                "offer_ids": [o.offer_id for o in updated.offers],
                "shares": [o.share for o in updated.offers],
            },
        )

        await self._audit.record(
            action=action,
            status="ok",
            campaign_id=stream.campaign_id,
            stream_id=stream.id,
            detail={
                "before": [
                    {"offer_id": o.offer_id, "share": o.share}
                    for o in stream.offers
                ],
                "after": [
                    {"offer_id": o.offer_id, "share": o.share}
                    for o in updated.offers
                ],
            },
        )
        return updated
