"""Сборка use case-ов и инфраструктурных адаптеров приложения."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine

from app.application.campaigns.creator import CampaignCreator
from app.application.campaigns.dtos import CampaignDefaults
from app.application.campaigns.editor import CampaignEditor
from app.application.campaigns.queries import CampaignQueries
from app.application.campaigns.streams import CampaignStreamsCreator
from app.application.catalog.service import Catalog
from app.application.health.check import HealthCheck
from app.application.idempotency import IdempotencyRepository
from app.application.operations.history import OperationHistory
from app.config import Settings, settings
from app.infrastructure.keitaro.client import KeitaroClient
from app.infrastructure.persistence.audit import SqlAuditRepository
from app.infrastructure.persistence.database import (
    build_engine,
    build_session_factory,
)
from app.infrastructure.persistence.idempotency import SqlIdempotencyRepository
from app.infrastructure.repositories.catalog.cached import (
    CachedCatalogRepository,
)
from app.infrastructure.repositories.health.database import SqlHealthRepository
from app.infrastructure.repositories.keitaro.campaigns import (
    KeitaroCampaignRepository,
)
from app.infrastructure.repositories.keitaro.catalog import (
    KeitaroCatalogRepository,
)


@dataclass(slots=True)
class ApplicationContainer:
    settings: Settings
    engine: AsyncEngine
    client: KeitaroClient
    catalog: Catalog
    campaign_creator: CampaignCreator
    campaign_editor: CampaignEditor
    campaign_queries: CampaignQueries
    operation_history: OperationHistory
    idempotency: IdempotencyRepository
    health_check: HealthCheck

    async def close(self) -> None:
        await self.client.aclose()
        await self.engine.dispose()


def build_container(config: Settings = settings) -> ApplicationContainer:
    engine = build_engine(config.database_url)
    session_factory = build_session_factory(engine)
    client = KeitaroClient(config)

    campaign_repository = KeitaroCampaignRepository(
        client, config.geo_redirect_url
    )
    catalog_repository = CachedCatalogRepository(
        KeitaroCatalogRepository(client),
        offers_ttl=config.offers_cache_ttl,
        references_ttl=config.reference_cache_ttl,
        session_factory=session_factory,
    )
    catalog_service = Catalog(catalog_repository)
    audit_repository = SqlAuditRepository(session_factory)
    health_repository = SqlHealthRepository(session_factory)

    streams_creator = CampaignStreamsCreator(campaign_repository)

    return ApplicationContainer(
        settings=config,
        engine=engine,
        client=client,
        catalog=catalog_service,
        campaign_creator=CampaignCreator(
            campaign_repository,
            audit_repository,
            streams_creator,
            defaults=CampaignDefaults(
                domain_id=config.default_domain_id,
                group_id=config.default_group_id,
                traffic_source_id=config.default_source_id,
            ),
            catalog=catalog_service,
        ),
        campaign_editor=CampaignEditor(
            campaign_repository, audit_repository, catalog=catalog_service
        ),
        campaign_queries=CampaignQueries(campaign_repository),
        operation_history=OperationHistory(audit_repository),
        idempotency=SqlIdempotencyRepository(session_factory),
        health_check=HealthCheck(health_repository),
    )
