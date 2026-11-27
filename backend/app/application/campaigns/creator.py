"""Сценарий создания кампании с компенсирующим удалением при сбое."""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Literal

from app.application.campaigns.dtos import CampaignDefaults, CreateCampaign
from app.application.catalog.service import Catalog
from app.application.errors import (
    ExternalServiceError,
    NotFoundError,
    ValidationError,
)
from app.application.offer.validation import ensure_offer_exists
from app.application.ports import (
    AuditRepository,
    CampaignCreationRepository,
    CampaignSnapshotRepository,
    CampaignStreamSetup,
)
from app.domain.campaigns.entities import Campaign, Stream, StreamOffer
from app.domain.catalog.entities import Reference
from app.domain.countries import is_country_code
from app.domain.shares import validate_offer_shares

logger = logging.getLogger(__name__)

type RemoteState = Literal["unchanged", "unknown", "leftover"]


@dataclass(slots=True)
class CreationProgress:
    """Что уже произошло в Keitaro в рамках одной попытки создания кампании.

    `remote_state` отвечает на вопрос, может ли в Keitaro остаться кампания:
    `unchanged` — записей не было либо они откатаны; `unknown` — ответ на
    запрос создания не получен; `leftover` — кампания создана и не удалена.
    """

    remote_state: RemoteState = "unchanged"
    campaign_id: int | None = None
    warnings: list[str] = field(default_factory=list)


class CampaignCreator:
    def __init__(
        self,
        repository: CampaignCreationRepository,
        audit: AuditRepository,
        streams_creator: CampaignStreamSetup,
        defaults: CampaignDefaults,
        catalog: Catalog | None = None,
        snapshots: CampaignSnapshotRepository | None = None,
    ) -> None:
        self._repository = repository
        self._audit = audit
        self._streams_creator = streams_creator
        self._defaults = defaults
        self._catalog = catalog
        self._snapshots = snapshots

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
        progress: CreationProgress | None = None,
    ) -> tuple[Campaign, list[Stream]]:
        """Создаёт кампанию с потоками; при сбое удаляет начатое из Keitaro."""
        progress = progress if progress is not None else CreationProgress()
        detail: dict[str, object] = {
            "name": name,
            "geo": geo,
            "offer_id": offer_id,
        }
        operation_id = await self._audit.begin(
            action="campaign.create",
            actor=actor,
            entity_type="campaign",
            detail=detail,
        )
        try:
            command = await self._prepare(
                name=name,
                alias=alias,
                geo=geo,
                offer_id=offer_id,
                domain_id=domain_id,
                group_id=group_id,
                source_id=source_id,
            )
        except BaseException as exc:
            await self._finish_safely(
                operation_id,
                status=(
                    "cancelled"
                    if isinstance(exc, asyncio.CancelledError)
                    else "failed"
                ),
                detail={**detail, "error": repr(exc)},
                error=str(exc),
            )
            raise

        campaign: Campaign | None = None
        try:
            progress.remote_state = "unknown"
            campaign = await self._repository.create_campaign(command)
            progress.campaign_id = campaign.id
            progress.remote_state = "leftover"
            campaign, streams = await self._configure(
                campaign, command, geo, offer_id, progress
            )
        except BaseException as exc:
            compensation = self._compensate(
                operation_id, campaign, detail, exc, progress
            )
            if isinstance(exc, asyncio.CancelledError):
                await asyncio.shield(compensation)
            else:
                await compensation
            raise

        await self._finish_safely(
            operation_id,
            status="ok",
            campaign_id=campaign.id,
            detail=(
                {**detail, "warnings": progress.warnings}
                if progress.warnings
                else detail
            ),
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

    async def _prepare(
        self,
        *,
        name: str,
        alias: str,
        geo: str,
        offer_id: int,
        domain_id: int | None,
        group_id: int | None,
        source_id: int | None,
    ) -> CreateCampaign:
        """Проверяет запрос и собирает команду; в Keitaro ничего не пишет."""
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
        return CreateCampaign(
            name=name,
            alias=alias,
            domain_id=resolved_domain_id,
            group_id=resolved_group_id,
            traffic_source_id=resolved_source_id,
        )

    async def _configure(
        self,
        campaign: Campaign,
        command: CreateCampaign,
        geo: str,
        offer_id: int,
        progress: CreationProgress,
    ) -> tuple[Campaign, list[Stream]]:
        """Создаёт потоки и сверяет сохранённую кампанию с отправленной."""
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
            campaign.id, geo=geo, offer_id=offer_id
        )
        verified = await self._repository.get_campaign(campaign.id)
        if verified.id != campaign.id:
            raise ExternalServiceError(
                f"Keitaro вернул кампанию #{verified.id} вместо "
                f"созданной кампании #{campaign.id}"
            )
        progress.warnings.extend(_verification_warnings(command, verified))
        if self._snapshots is not None:
            await self._save_snapshot(
                self._snapshots, verified, streams, progress
            )
        return verified, streams

    async def _save_snapshot(
        self,
        snapshots: CampaignSnapshotRepository,
        campaign: Campaign,
        streams: list[Stream],
        progress: CreationProgress,
    ) -> None:
        """Локальная копия: её сбой не отменяет создание в Keitaro."""
        try:
            await snapshots.save(campaign, streams)
        except Exception as exc:
            progress.warnings.append(
                "Локальный снимок кампании не сохранён: кампания создана "
                "в Keitaro, но недоступна в истории этого сервиса"
            )
            logger.error(
                "не удалось сохранить снимок кампании",
                extra={
                    "campaign_id": campaign.id,
                    "exception_type": type(exc).__name__,
                },
            )

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

    async def _compensate(
        self,
        operation_id: int,
        campaign: Campaign | None,
        detail: dict[str, object],
        exc: BaseException,
        progress: CreationProgress,
    ) -> None:
        """Удаляет созданную кампанию и закрывает запись аудита."""
        if campaign is None:
            # Запрос создания не дошёл или отклонён. Кампании точно нет только
            # при явном отказе 4xx; при таймауте и 5xx итог неизвестен.
            rejected = _rejected_by_keitaro(exc)
            if rejected:
                progress.remote_state = "unchanged"
            await self._finish_safely(
                operation_id,
                status="failed" if rejected else "unknown",
                detail={**detail, "error": repr(exc)},
                error=str(exc),
            )
            return

        logger.warning(
            "откат кампании после ошибки",
            extra={
                "campaign_id": campaign.id,
                "exception_type": type(exc).__name__,
                "geo": detail.get("geo"),
                "offer_id": detail.get("offer_id"),
            },
        )
        campaign_detail = {**detail, "campaign_id": campaign.id}
        error = str(exc)
        status = "rolled_back"
        try:
            await self._repository.delete_campaign(campaign.id)
            progress.remote_state = "unchanged"
        except Exception as delete_exc:
            status = "rollback_failed"
            progress.remote_state = "leftover"
            campaign_detail["rollback_error"] = str(delete_exc)
            error = f"{exc}; rollback failed: {delete_exc}"
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
            detail=campaign_detail,
            entity_id=campaign.id,
            error=error,
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


def _rejected_by_keitaro(exc: BaseException) -> bool:
    """Keitaro ответил 4xx на запрос создания — записи в нём не появилось."""
    return (
        isinstance(exc, ExternalServiceError)
        and exc.status is not None
        and 400 <= exc.status < 500
    )


def _require_reference(
    references: list[Reference], item_id: int, label: str
) -> None:
    if not any(reference.id == item_id for reference in references):
        raise NotFoundError(f"{label} #{item_id} не найден в каталоге Keitaro")


_FIELD_LABELS = {
    "alias": "алиас",
    "domain_id": "домен",
    "group_id": "группу",
    "traffic_source_id": "источник трафика",
}


def _verification_warnings(
    sent: CreateCampaign, stored: Campaign
) -> list[str]:
    """Поля, которые Keitaro сохранил иначе, чем их отправили."""
    warnings: list[str] = []
    if stored.name != sent.name:
        warnings.append(f"Keitaro сохранил название как «{stored.name}»")
    expected = {
        "alias": sent.alias,
        "domain_id": sent.domain_id,
        "group_id": sent.group_id,
        "traffic_source_id": sent.traffic_source_id,
    }
    for field_name, value in expected.items():
        actual = getattr(stored, field_name)
        if actual is not None and actual != value:
            warnings.append(
                f"Keitaro сохранил {_FIELD_LABELS[field_name]} "
                f"как {actual!r} вместо {value!r}"
            )
    return warnings
