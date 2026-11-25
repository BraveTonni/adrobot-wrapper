"""Сценарий создания кампании с компенсирующим удалением при сбое."""

import asyncio
import logging

from app.application.campaigns.dtos import CampaignDefaults, CreateCampaign
from app.application.offer.validation import ensure_offer_exists
from app.application.ports import (
    AuditRepository,
    CampaignCreationRepository,
    CampaignStreamSetup,
)
from app.domain.campaigns.entities import Campaign, Stream

logger = logging.getLogger(__name__)


class CampaignCreator:
    def __init__(
        self,
        repository: CampaignCreationRepository,
        audit: AuditRepository,
        streams_creator: CampaignStreamSetup,
        defaults: CampaignDefaults,
    ) -> None:
        self._repository = repository
        self._audit = audit
        self._streams_creator = streams_creator
        self._defaults = defaults

    async def create(
        self,
        *,
        name: str,
        alias: str,
        geo: str,
        offer_id: int,
        domain_id: int | None = None,
        group_id: int | None = None,
        source_id: int | None = None,
    ) -> tuple[Campaign, list[Stream]]:
        await ensure_offer_exists(self._repository, offer_id)
        operation_id = await self._audit.begin(
            action="campaign.create",
            detail={"name": name, "geo": geo, "offer_id": offer_id},
        )
        campaign: Campaign | None = None
        try:
            campaign = await self._repository.create_campaign(
                CreateCampaign(
                    name=name,
                    alias=alias,
                    domain_id=(
                        self._defaults.domain_id
                        if domain_id is None
                        else domain_id
                    ),
                    group_id=(
                        self._defaults.group_id
                        if group_id is None
                        else group_id
                    ),
                    traffic_source_id=(
                        self._defaults.traffic_source_id
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
            streams = await self._streams_creator.create(
                campaign.id, geo=geo, offer_id=offer_id
            )
        except asyncio.CancelledError as exc:
            if campaign is None:
                await asyncio.shield(
                    self._finish_safely(
                        operation_id,
                        status="unknown",
                        detail={"error": repr(exc), "offer_id": offer_id},
                    )
                )
            else:
                await asyncio.shield(
                    self._rollback(operation_id, campaign, geo, offer_id, exc)
                )
            raise
        except Exception as exc:
            if campaign is None:
                await self._finish_safely(
                    operation_id,
                    status="unknown",
                    detail={"error": repr(exc), "offer_id": offer_id},
                )
            else:
                await self._rollback(
                    operation_id, campaign, geo, offer_id, exc
                )
            raise

        await self._finish_safely(
            operation_id,
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

    async def _rollback(
        self,
        operation_id: int,
        campaign: Campaign,
        geo: str,
        offer_id: int,
        cause: BaseException,
    ) -> None:
        logger.warning(
            "откат кампании после ошибки",
            extra={
                "campaign_id": campaign.id,
                "exception_type": type(cause).__name__,
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
            await self._repository.delete_campaign(campaign.id)
        except Exception as delete_exc:
            status = "rollback_failed"
            detail["rollback_error"] = str(delete_exc)
            logger.error(
                "откат не удался: кампания осталась в Keitaro",
                extra={
                    "campaign_id": campaign.id,
                    "rollback_exception_type": type(delete_exc).__name__,
                },
            )
        await self._finish_safely(
            operation_id,
            status=status,
            campaign_id=campaign.id,
            detail=detail,
        )

    async def _finish_safely(
        self,
        operation_id: int,
        *,
        status: str,
        campaign_id: int | None = None,
        detail: dict[str, object] | None = None,
    ) -> None:
        try:
            await self._audit.finish(
                operation_id,
                status=status,
                campaign_id=campaign_id,
                detail=detail,
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
