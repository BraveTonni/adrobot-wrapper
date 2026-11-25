"""Эндпоинты API - только HTTP: валидация, вызов сервиса, ответ."""

from fastapi import APIRouter, Query
from sqlalchemy import text

from app.api.deps import (
    AuditDep,
    CatalogDep,
    ClientDep,
    CreatorDep,
    EditorDep,
    SessionDep,
    SettingsDep,
)
from app.api.schemas import (
    CampaignCreate,
    CampaignOut,
    OfferAdd,
    StreamOut,
    campaign_out,
    stream_out,
)
from app.services.catalog import Catalog

router = APIRouter(prefix="/api")


@router.get("/health")
async def health(session: SessionDep) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ok"}


@router.get("/references")
async def references(catalog: CatalogDep) -> dict[str, object]:
    refs = await catalog.references()
    return {
        "domains": [{"id": d.id, "name": d.name} for d in refs.domains],
        "groups": [{"id": g.id, "name": g.name} for g in refs.groups],
        "sources": [{"id": s.id, "name": s.name} for s in refs.sources],
    }


@router.get("/offers")
async def offers(
    catalog: CatalogDep,
    search: str = Query(default="", max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[dict[str, object]]:
    items = await catalog.search_offers(search, limit)
    return [{"id": o.id, "name": o.name} for o in items]


@router.get("/campaigns")
async def list_campaigns(
    client: ClientDep,
    config: SettingsDep,
    search: str = Query(default="", max_length=100),
) -> list[dict[str, object]]:
    campaigns = await client.list_campaigns(config.campaign_search_limit)
    if search:
        needle = search.lower()
        campaigns = [c for c in campaigns if needle in c.name.lower()]

    return [{"id": c.id, "name": c.name, "alias": c.alias} for c in campaigns]


@router.post("/campaigns", status_code=201)
async def create_campaign(
    body: CampaignCreate,
    creator: CreatorDep,
    catalog: CatalogDep,
    config: SettingsDep,
) -> CampaignOut:
    campaign, streams = await creator.create(
        name=body.name,
        geo=body.geo,
        offer_id=body.offer_id,
        domain_id=body.domain_id,
        group_id=body.group_id,
        source_id=body.source_id,
    )
    names = await _offer_names(catalog)

    return campaign_out(campaign, streams, names, config.keitaro_admin_url)


@router.get("/campaigns/{campaign_id}")
async def get_campaign(
    campaign_id: int,
    client: ClientDep,
    catalog: CatalogDep,
    config: SettingsDep,
) -> CampaignOut:
    campaign = await client.get_campaign(campaign_id)
    streams = await client.list_streams(campaign_id)
    names = await _offer_names(catalog)

    return campaign_out(campaign, streams, names, config.keitaro_admin_url)


@router.post(
    "/campaigns/{campaign_id}/streams/{stream_id}/offers", status_code=201
)
async def add_offer(
    campaign_id: int,
    stream_id: int,
    body: OfferAdd,
    editor: EditorDep,
    catalog: CatalogDep,
) -> StreamOut:
    stream = await editor.add_offer(campaign_id, stream_id, body.offer_id)
    names = await _offer_names(catalog)

    return stream_out(stream, names)


@router.delete(
    "/campaigns/{campaign_id}/streams/{stream_id}/offers/{offer_id}"
)
async def remove_offer(
    campaign_id: int,
    stream_id: int,
    offer_id: int,
    editor: EditorDep,
    catalog: CatalogDep,
) -> StreamOut:
    stream = await editor.remove_offer(campaign_id, stream_id, offer_id)
    names = await _offer_names(catalog)

    return stream_out(stream, names)


@router.get("/operations")
async def operations(audit: AuditDep) -> list[dict[str, object]]:
    items = await audit.recent()
    return [
        {
            "id": op.id,
            "created_at": op.created_at.isoformat(),
            "action": op.action,
            "campaign_id": op.campaign_id,
            "stream_id": op.stream_id,
            "status": op.status,
            "detail": op.detail,
        }
        for op in items
    ]


async def _offer_names(catalog: Catalog) -> dict[int, str]:
    return {offer.id: offer.name for offer in await catalog.offers()}
