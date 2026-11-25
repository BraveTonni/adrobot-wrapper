"""Разрешение прикладных сценариев из контейнера приложения."""

from typing import Annotated, cast

from fastapi import Depends, Request

from app.application.campaigns.creator import CampaignCreator
from app.application.campaigns.editor import CampaignEditor
from app.application.campaigns.queries import CampaignQueries
from app.application.catalog.service import Catalog
from app.application.health.check import HealthCheck
from app.application.operations.history import OperationHistory
from app.config import Settings


def get_catalog(request: Request) -> Catalog:
    return cast(Catalog, request.app.state.container.catalog)


def get_campaign_creator(request: Request) -> CampaignCreator:
    return cast(CampaignCreator, request.app.state.container.campaign_creator)


def get_campaign_editor(request: Request) -> CampaignEditor:
    return cast(CampaignEditor, request.app.state.container.campaign_editor)


def get_campaign_queries(request: Request) -> CampaignQueries:
    return cast(CampaignQueries, request.app.state.container.campaign_queries)


def get_operation_history(request: Request) -> OperationHistory:
    return cast(
        OperationHistory, request.app.state.container.operation_history
    )


def get_health_check(request: Request) -> HealthCheck:
    return cast(HealthCheck, request.app.state.container.health_check)


def get_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.container.settings)


CatalogDep = Annotated[Catalog, Depends(get_catalog)]
CreatorDep = Annotated[CampaignCreator, Depends(get_campaign_creator)]
EditorDep = Annotated[CampaignEditor, Depends(get_campaign_editor)]
CampaignQueriesDep = Annotated[CampaignQueries, Depends(get_campaign_queries)]
OperationHistoryDep = Annotated[
    OperationHistory, Depends(get_operation_history)
]
HealthCheckDep = Annotated[HealthCheck, Depends(get_health_check)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
