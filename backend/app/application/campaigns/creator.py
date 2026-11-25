"""Сценарий создания кампании с компенсирующим удалением при сбое."""

import asyncio
import logging
from collections.abc import Sequence

from app.application.catalog.dtos import References
from app.application.catalog.service import Catalog
from app.application.campaigns.dtos import CampaignDefaults, CreateCampaign
from app.application.errors import NotFoundError, ValidationError
from app.application.offer.validation import ensure_offer_exists
from app.application.ports import (
    AuditRepository,
    CampaignCreationRepository,
    CampaignStreamSetup,
)
from app.domain.campaigns.entities import Campaign, Stream, StreamOffer
from app.domain.catalog.entities import Reference
from app.domain.countries import is_country_code
from app.domain.shares import validate_offer_shares

logger = logging.getLogger(__name__)


class CampaignCreator:
    def __init__(
        self,
        repository: CampaignCreationRepository,
        audit: AuditRepository,
        streams_creator: CampaignStreamSetup,
        defaults: CampaignDefaults,
        catalog: Catalog | None = None,
    ) -> None:
        self._repository = repository
        self._audit = audit
        self._streams_creator = streams_creator
        self._defaults = defaults
        self._catalog = catalog

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
        actor: str = "unknown",
    ) -> tuple[Campaign, list[Stream]]:
        operation_id = await self._audit.begin(
            action="campaign.create",
            actor=actor,
            entity_type="campaign",
            detail={"name": name, "geo": geo, "offer_id": offer_id},
        )
        campaign: Campaign | None = None
        try:
            normalized_geo = geo.strip().upper()
            if not is_country_code(normalized_geo):
                raise ValidationError(
                    f"{geo!r} не является кодом ISO 3166-1 alpha-2"
                )

            resolved_domain_id = (
                self._defaults.domain_id if domain_id is None else domain_id
            )
            resolved_group_id = (
                self._defaults.group_id if group_id is None else group_id
            )
            resolved_source_id = (
                self._defaults.traffic_source_id
                if source_id is None
                else source_id
            )
            await self._validate_catalog(
                offer_id,
                resolved_domain_id,
                resolved_group_id,
                resolved_source_id,
            )
            validate_offer_shares(
                [StreamOffer(offer_id=offer_id, share=100, state="active")]
            )
            campaign = await self._repository.create_campaign(
                CreateCampaign(
                    name=name,
                    alias=alias,
                    domain_id=resolved_domain_id,
                    group_id=resolved_group_id,
                    traffic_source_id=resolved_source_id,
                )
            )
            logger.info(
                "кампания создана",
                extra={
                    "campaign_id": campaign.id,
                    "campaign_name": campaign.name,
                    "geo": geo,
                    "offer_id": offer_id,
                },
            )
            streams = await self._streams_creator.create(
                campaign.id, geo=normalized_geo, offer_id=offer_id
            )
        except asyncio.CancelledError as exc:
            if campaign is None:
                await asyncio.shield(
                    self._finish_safely(
                        operation_id,
                        status="unknown",
                        detail={"error": repr(exc), "offer_id": offer_id},
                        error=repr(exc),
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
                    status="failed",
                    detail={"error": repr(exc), "offer_id": offer_id},
                    error=str(exc),
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
            entity_id=campaign.id,
            after_payload={
                "campaign": {
                    "id": campaign.id,
                    "name": campaign.name,
                    "alias": campaign.alias,
                },
                "streams": [
                    {
                        "id": stream.id,
                        "type": stream.type,
                        "schema": stream.schema,
                        "offers": [
                            {
                                "offer_id": offer.offer_id,
                                "share": offer.share,
                                "state": offer.state,
                            }
                            for offer in stream.offers
                        ],
                    }
                    for stream in streams
                ],
            },
        )
        return campaign, streams

    async def _validate_catalog(
        self,
        offer_id: int,
        domain_id: int,
        group_id: int,
        source_id: int,
    ) -> None:
        if self._catalog is None:
            await ensure_offer_exists(self._repository, offer_id)
            return

        offers, references = await asyncio.gather(
            self._catalog.offers(), self._catalog.references()
        )
        if not any(offer.id == offer_id for offer in offers):
            raise NotFoundError(
                f"Оффер #{offer_id} не найден в каталоге Keitaro"
            )
        _require_reference(references.domains, domain_id, "Домен")
        _require_reference(references.groups, group_id, "Группа кампаний")
        _require_reference(references.sources, source_id, "Источник трафика")

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
        rollback_error: str | None = None
        detail: dict[str, object] = {
            "error": repr(cause),
            "geo": geo,
            "offer_id": offer_id,
        }
        try:
            await self._repository.delete_campaign(campaign.id)
        except Exception as delete_exc:
            status = "rollback_failed"
            rollback_error = str(delete_exc)
            detail["rollback_error"] = rollback_error
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
            entity_id=campaign.id,
            error=(
                f"{cause}; rollback failed: {rollback_error}"
                if status == "rollback_failed"
                else str(cause)
            ),
        )

    async def _finish_safely(
        self,
        operation_id: int,
        *,
        status: str,
        campaign_id: int | None = None,
        detail: dict[str, object] | None = None,
        entity_id: int | None = None,
        after_payload: dict[str, object] | list[object] | None = None,
        error: str | None = None,
    ) -> None:
        try:
            await self._audit.finish(
                operation_id,
                status=status,
                campaign_id=campaign_id,
                detail=detail,
                entity_id=entity_id,
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


def _require_reference(
    references: Sequence[Reference], item_id: int, label: str
) -> None:
    if not any(reference.id == item_id for reference in references):
        raise NotFoundError(
            f"{label} #{item_id} не найден в каталоге Keitaro"
        )
