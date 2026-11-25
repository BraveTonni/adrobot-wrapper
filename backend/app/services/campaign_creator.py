"""Создание кампании: гео-поток на Google и поток с оффером.

Keitaro не имеет транзакций, поэтому атомарность эмулируется:
кампания -> гео-поток -> поток оффера -> проверка порядка,
и если шаг после создания кампании упал, кампания удаляется
(DELETE /campaigns/{id} удаляет и потоки).
"""

import asyncio
import logging

from app.config import Settings, settings
from app.keitaro.client import KeitaroClient
from app.keitaro.errors import KeitaroError
from app.keitaro.schemas import (
    Campaign,
    CampaignCreate,
    Stream,
    StreamCreate,
    StreamFilter,
)
from app.services.errors import NotFoundError
from app.services.ports import AuditLog

logger = logging.getLogger(__name__)

GEO_STREAM_POSITION = 1
OFFER_STREAM_POSITION = 2


class CampaignCreator:
    def __init__(
        self,
        client: KeitaroClient,
        audit: AuditLog,
        *,
        config: Settings = settings,
    ) -> None:
        self._client = client
        self._audit = audit
        self._config = config

    async def create(
        self,
        *,
        name: str,
        geo: str,
        offer_id: int,
        domain_id: int | None = None,
        group_id: int | None = None,
        source_id: int | None = None,
    ) -> tuple[Campaign, list[Stream]]:
        await self._check_offer(offer_id)

        campaign = await self._client.create_campaign(
            CampaignCreate(
                name=name,
                domain_id=(
                    self._config.default_domain_id
                    if domain_id is None
                    else domain_id
                ),
                group_id=(
                    self._config.default_group_id
                    if group_id is None
                    else group_id
                ),
                traffic_source_id=(
                    self._config.default_source_id
                    if source_id is None
                    else source_id
                ),
            )
        )
        logger.info(
            "кампания создана",
            extra={
                "campaign_id": campaign.id,
                "name": campaign.name,
                "geo": geo,
                "offer_id": offer_id,
            },
        )

        try:
            streams = await self._create_streams(
                campaign.id, geo=geo, offer_id=offer_id
            )
        except asyncio.CancelledError as exc:
            await asyncio.shield(self._rollback(campaign, geo, offer_id, exc))
            raise
        except Exception as exc:
            await self._rollback(campaign, geo, offer_id, exc)
            raise

        await self._audit.record(
            action="campaign.create",
            status="ok",
            campaign_id=campaign.id,
            detail={
                "name": campaign.name,
                "geo": geo,
                "offer_id": offer_id,
                "stream_ids": [stream.id for stream in streams],
            },
        )
        return campaign, streams

    async def _check_offer(self, offer_id: int) -> None:
        try:
            await self._client.get_offer(offer_id)
        except KeitaroError as exc:
            if exc.status == 404:
                raise NotFoundError(
                    f"Оффер #{offer_id} не найден в Keitaro"
                ) from exc
            raise

    async def _create_streams(
        self, campaign_id: int, *, geo: str, offer_id: int
    ) -> list[Stream]:
        geo_stream = await self._client.create_stream(
            StreamCreate(
                campaign_id=campaign_id,
                name=f"Geo {geo}",
                type="regular",
                schema="redirect",
                position=GEO_STREAM_POSITION,
                action_type="http",
                action_payload=self._config.geo_redirect_url,
                filters=[
                    StreamFilter(name="country", mode="accept", payload=[geo])
                ],
            )
        )
        offer_stream = await self._client.create_stream(
            StreamCreate(
                campaign_id=campaign_id,
                name="Offers",
                type="default",
                schema="landings",
                position=OFFER_STREAM_POSITION,
                offers=[
                    {"offer_id": offer_id, "share": 100, "state": "active"}
                ],
            )
        )

        # Читаем фактический порядок: гео-поток должен быть первым.
        streams = await self._client.list_streams(campaign_id)
        order = [stream.id for stream in streams]
        if order[:2] != [geo_stream.id, offer_stream.id]:
            raise KeitaroError(
                f"неожиданный порядок потоков {order}: "
                f"гео-поток {geo_stream.id} должен быть первым"
            )
        return streams

    async def _rollback(
        self,
        campaign: Campaign,
        geo: str,
        offer_id: int,
        cause: BaseException,
    ) -> None:
        logger.warning(
            "откат кампании после ошибки",
            extra={
                "campaign_id": campaign.id,
                "error": repr(cause),
                "geo": geo,
                "offer_id": offer_id,
            },
        )
        status = "rolled_back"
        detail: dict[str, object] = {
            "error": repr(cause),
            "geo": geo,
            "offer_id": offer_id,
        }
        try:
            await self._client.delete_campaign(campaign.id)
        except KeitaroError as delete_exc:
            # Кампания осталась в трекере: журнал поможет её найти.
            status = "rollback_failed"
            detail["rollback_error"] = str(delete_exc)
            logger.error(
                "откат не удался: кампания осталась в Keitaro",
                extra={
                    "campaign_id": campaign.id,
                    "rollback_error": str(delete_exc),
                },
            )
        await self._audit.record(
            action="campaign.create",
            status=status,
            campaign_id=campaign.id,
            detail=detail,
        )
