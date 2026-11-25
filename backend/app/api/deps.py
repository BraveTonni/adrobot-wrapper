"""Зависимости FastAPI - сборка объектов из состояния приложения."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.keitaro.client import KeitaroClient
from app.services.campaign_creator import CampaignCreator
from app.services.campaign_editor import CampaignEditor
from app.services.catalog import Catalog
from app.storage.audit import AuditLog


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    factory: async_sessionmaker[AsyncSession] = (
        request.app.state.session_factory
    )
    async with factory() as session:
        yield session


def get_client(request: Request) -> KeitaroClient:
    client: KeitaroClient = request.app.state.client
    return client


def get_catalog(request: Request) -> Catalog:
    catalog: Catalog = request.app.state.catalog
    return catalog


def get_creator(
    client: Annotated[KeitaroClient, Depends(get_client)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CampaignCreator:
    return CampaignCreator(client, AuditLog(session))


def get_editor(
    client: Annotated[KeitaroClient, Depends(get_client)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CampaignEditor:
    return CampaignEditor(client, AuditLog(session))


SessionDep = Annotated[AsyncSession, Depends(get_session)]
ClientDep = Annotated[KeitaroClient, Depends(get_client)]
CatalogDep = Annotated[Catalog, Depends(get_catalog)]
CreatorDep = Annotated[CampaignCreator, Depends(get_creator)]
EditorDep = Annotated[CampaignEditor, Depends(get_editor)]
