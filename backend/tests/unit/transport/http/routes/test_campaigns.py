from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request

from app.application.campaigns.alias import build_campaign_alias
from app.config import Settings
from app.domain.campaigns.entities import Campaign, Stream, StreamOffer
from app.domain.catalog.entities import Offer
from app.transport.http.routes.campaigns import (
    add_offer,
    create_campaign,
    get_campaign,
    list_campaigns,
    remove_offer,
)
from app.transport.http.schemas.campaigns import CampaignCreate
from app.transport.http.schemas.streams import OfferAdd


def request_with_actor() -> Request:
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/v1/campaigns",
            "raw_path": b"/api/v1/campaigns",
            "query_string": b"",
            "headers": [(b"x-user", b"qa-user")],
            "client": ("127.0.0.1", 1234),
            "server": ("testserver", 80),
        }
    )


@pytest.mark.asyncio
async def test_list_campaigns_passes_search_and_limit_to_query() -> None:
    queries = SimpleNamespace(
        search=AsyncMock(
            return_value=[Campaign(id=1, name="Spring", alias="spring")]
        )
    )
    config = Settings(_env_file=None, campaign_search_limit=23)

    result = await list_campaigns(queries, config, search="SPR")

    assert [item.model_dump() for item in result] == [
        {"id": 1, "name": "Spring", "alias": "spring"}
    ]
    queries.search.assert_awaited_once_with("SPR", 23)


@pytest.mark.asyncio
async def test_create_campaign_passes_validated_options_to_use_case() -> None:
    campaign = Campaign(id=9, name="Launch")
    stream = Stream(
        id=10,
        campaign_id=9,
        name="Offers",
        schema="landings",
        offers=[StreamOffer(offer_id=2, share=100)],
    )
    creator = SimpleNamespace(
        create=AsyncMock(return_value=(campaign, [stream]))
    )
    catalog = SimpleNamespace(offers=AsyncMock(return_value=[Offer(2, "O")]))
    config = Settings(_env_file=None, keitaro_admin_url="https://panel/")
    idempotency = SimpleNamespace(
        reserve=AsyncMock(return_value=("reserved", None)),
        complete=AsyncMock(),
    )
    body = CampaignCreate(
        name="Launch",
        geo="US",
        offer_id=2,
        domain_id=11,
        group_id=12,
        source_id=13,
    )

    result = await create_campaign(
        request_with_actor(),
        body,
        creator,
        catalog,
        config,
        idempotency,
        idempotency_key="request-key-1234567890",
    )

    assert result.admin_url == "https://panel/#!/campaign.editor/9"
    assert result.streams[0].offers[0].name == "O"
    creator.create.assert_awaited_once_with(
        name="Launch",
        alias=build_campaign_alias("Launch", "request-key-1234567890"),
        geo="US",
        offer_id=2,
        domain_id=11,
        group_id=12,
        source_id=13,
        actor="qa-user",
    )
    idempotency.complete.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_campaign_returns_query_result_with_offer_names() -> None:
    campaign = Campaign(id=9, name="Launch")
    stream = Stream(
        id=10,
        campaign_id=9,
        name="Offers",
        schema="landings",
        offers=[StreamOffer(offer_id=2, share=100)],
    )
    queries = SimpleNamespace(
        get_with_streams=AsyncMock(return_value=(campaign, [stream]))
    )
    catalog = SimpleNamespace(offers=AsyncMock(return_value=[Offer(2, "O")]))
    config = Settings(_env_file=None)

    result = await get_campaign(9, queries, catalog, config)

    assert result.id == 9
    assert result.streams[0].offers[0].name == "O"


@pytest.mark.asyncio
async def test_add_offer_returns_stream_response() -> None:
    stream = Stream(id=2, campaign_id=1, name="Offers", schema="landings")
    editor = SimpleNamespace(add_offer=AsyncMock(return_value=stream))
    catalog = SimpleNamespace(offers=AsyncMock(return_value=[]))

    result = await add_offer(
        request_with_actor(), 1, 2, OfferAdd(offer_id=3), editor, catalog
    )

    assert result.id == 2
    editor.add_offer.assert_awaited_once_with(1, 2, 3, actor="qa-user")


@pytest.mark.asyncio
async def test_remove_offer_returns_stream_response() -> None:
    stream = Stream(id=2, campaign_id=1, name="Offers", schema="landings")
    editor = SimpleNamespace(remove_offer=AsyncMock(return_value=stream))
    catalog = SimpleNamespace(offers=AsyncMock(return_value=[]))

    result = await remove_offer(request_with_actor(), 1, 2, 3, editor, catalog)

    assert result.id == 2
    editor.remove_offer.assert_awaited_once_with(1, 2, 3, actor="qa-user")
