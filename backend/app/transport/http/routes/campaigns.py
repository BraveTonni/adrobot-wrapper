"""HTTP-маршруты чтения и изменения кампаний."""

from fastapi import APIRouter, Query

from app.transport.http.deps import (
    CampaignQueriesDep,
    CatalogDep,
    CreatorDep,
    EditorDep,
    SettingsDep,
)
from app.transport.http.presenters.campaigns import CampaignResponseFactory
from app.transport.http.schemas.campaigns import (
    CampaignCreate,
    CampaignOut,
    CampaignSummaryOut,
)
from app.transport.http.schemas.streams import OfferAdd, StreamOut

router = APIRouter()


@router.get("/campaigns", response_model=list[CampaignSummaryOut])
async def list_campaigns(
    queries: CampaignQueriesDep,
    config: SettingsDep,
    search: str = Query(default="", max_length=100),
) -> list[CampaignSummaryOut]:
    campaigns = await queries.search(search, config.campaign_search_limit)
    return CampaignResponseFactory.campaigns(campaigns)


@router.post("/campaigns", status_code=201, response_model=CampaignOut)
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
    offers = await catalog.offers()

    return CampaignResponseFactory.campaign(
        campaign, streams, offers, config.keitaro_admin_url
    )


@router.get("/campaigns/{campaign_id}", response_model=CampaignOut)
async def get_campaign(
    campaign_id: int,
    queries: CampaignQueriesDep,
    catalog: CatalogDep,
    config: SettingsDep,
) -> CampaignOut:
    campaign, streams = await queries.get_with_streams(campaign_id)
    offers = await catalog.offers()

    return CampaignResponseFactory.campaign(
        campaign, streams, offers, config.keitaro_admin_url
    )


@router.post(
    "/campaigns/{campaign_id}/streams/{stream_id}/offers",
    status_code=201,
    response_model=StreamOut,
)
async def add_offer(
    campaign_id: int,
    stream_id: int,
    body: OfferAdd,
    editor: EditorDep,
    catalog: CatalogDep,
) -> StreamOut:
    stream = await editor.add_offer(campaign_id, stream_id, body.offer_id)
    return CampaignResponseFactory.stream(stream, await catalog.offers())


@router.delete(
    "/campaigns/{campaign_id}/streams/{stream_id}/offers/{offer_id}",
    response_model=StreamOut,
)
async def remove_offer(
    campaign_id: int,
    stream_id: int,
    offer_id: int,
    editor: EditorDep,
    catalog: CatalogDep,
) -> StreamOut:
    stream = await editor.remove_offer(campaign_id, stream_id, offer_id)
    return CampaignResponseFactory.stream(stream, await catalog.offers())
