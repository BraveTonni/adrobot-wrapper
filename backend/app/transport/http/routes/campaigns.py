"""HTTP-маршруты чтения и изменения кампаний."""

import hashlib
import json

from fastapi import APIRouter, Header, HTTPException, Query, Request

from app.application.campaigns.alias import build_campaign_alias
from app.application.errors import ExternalServiceError, NotFoundError
from app.transport.http.audit import audit_actor
from app.transport.http.deps import (
    CampaignQueriesDep,
    CatalogDep,
    CreatorDep,
    EditorDep,
    SettingsDep,
)
from app.transport.http.idempotency_deps import IdempotencyDep
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


@router.post(
    "/campaigns",
    status_code=201,
    response_model=CampaignOut,
)
async def create_campaign(
    request: Request,
    body: CampaignCreate,
    creator: CreatorDep,
    catalog: CatalogDep,
    config: SettingsDep,
    idempotency: IdempotencyDep,
    idempotency_key: str | None = Header(
        default=None, alias="Idempotency-Key", min_length=16, max_length=128
    ),
) -> CampaignOut:
    if idempotency_key is None:
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key header is required for campaign creation",
        )
    payload = body.model_dump(mode="json")
    request_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    state, saved_response = await idempotency.reserve(
        idempotency_key, request_hash
    )
    if state == "mismatch":
        raise HTTPException(
            status_code=409,
            detail="Idempotency-Key was already used for another request",
        )
    if state == "pending":
        raise HTTPException(
            status_code=409,
            detail="A request with this Idempotency-Key is still pending",
        )
    if state == "stale":
        raise HTTPException(
            status_code=409,
            detail=(
                "This Idempotency-Key is stale. Reconcile the campaign in "
                "Keitaro, then release it through the operations endpoint."
            ),
        )
    if state == "complete" and saved_response is not None:
        return CampaignOut.model_validate(saved_response)

    try:
        campaign, streams = await creator.create(
            name=body.name,
            alias=build_campaign_alias(body.name, idempotency_key),
            geo=body.geo,
            offer_id=body.offer_id,
            domain_id=body.domain_id,
            group_id=body.group_id,
            source_id=body.source_id,
            actor=audit_actor(request),
        )
    except NotFoundError:
        await idempotency.release(idempotency_key)
        raise
    try:
        offers = await catalog.offers()
    except ExternalServiceError:
        # Enrichment is optional after the Keitaro mutation has succeeded.
        offers = []

    response = CampaignResponseFactory.campaign(
        campaign, streams, offers, config.keitaro_admin_url
    )
    await idempotency.complete(
        idempotency_key, response.model_dump(mode="json")
    )
    return response


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
    request: Request,
    campaign_id: int,
    stream_id: int,
    body: OfferAdd,
    editor: EditorDep,
    catalog: CatalogDep,
) -> StreamOut:
    stream = await editor.add_offer(
        campaign_id, stream_id, body.offer_id, actor=audit_actor(request)
    )
    return CampaignResponseFactory.stream(stream, await catalog.offers())


@router.delete(
    "/campaigns/{campaign_id}/streams/{stream_id}/offers/{offer_id}",
    response_model=StreamOut,
)
async def remove_offer(
    request: Request,
    campaign_id: int,
    stream_id: int,
    offer_id: int,
    editor: EditorDep,
    catalog: CatalogDep,
) -> StreamOut:
    stream = await editor.remove_offer(
        campaign_id, stream_id, offer_id, actor=audit_actor(request)
    )
    return CampaignResponseFactory.stream(stream, await catalog.offers())
