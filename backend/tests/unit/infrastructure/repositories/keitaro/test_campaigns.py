from unittest.mock import AsyncMock

import pytest

from app.application.campaigns.dtos import CreateCampaign, CreateStream
from app.domain.campaigns.entities import Campaign, Stream, StreamOffer
from app.infrastructure.keitaro.client import KeitaroClient
from app.infrastructure.keitaro.schemas import Campaign as KeitaroCampaign
from app.infrastructure.keitaro.schemas import Stream as KeitaroStream
from app.infrastructure.repositories.keitaro.campaigns import (
    KeitaroCampaignRepository,
)


@pytest.mark.asyncio
async def test_create_campaign_maps_command_and_response() -> None:
    client = AsyncMock(spec=KeitaroClient)
    client.create_campaign.return_value = KeitaroCampaign(
        id=7, name="Launch", alias="launch"
    )
    repository = KeitaroCampaignRepository(client)
    command = CreateCampaign(
        name="Launch",
        alias="launch-123456789abc",
        domain_id=1,
        group_id=2,
        traffic_source_id=3,
    )

    result = await repository.create_campaign(command)

    request = client.create_campaign.await_args.args[0]
    assert request.to_api() == {
        "name": "Launch",
        "alias": "launch-123456789abc",
        "type": "position",
        "domain_id": 1,
        "group_id": 2,
        "traffic_source_id": 3,
    }
    assert result == Campaign(id=7, name="Launch", alias="launch")


@pytest.mark.asyncio
async def test_create_stream_sends_geo_filter_redirect_and_action_type() -> (
    None
):
    client = AsyncMock(spec=KeitaroClient)
    client.create_stream.return_value = KeitaroStream.model_validate(
        {"id": 8, "campaign_id": 7, "schema": "redirect"}
    )
    repository = KeitaroCampaignRepository(client)

    stream = await repository.create_stream(
        CreateStream(
            campaign_id=7,
            name="Geo US",
            type="regular",
            schema="redirect",
            position=1,
            action_type="http",
            action_payload="https://google.com",
            filters=(
                {"name": "country", "mode": "accept", "payload": ["US"]},
            ),
        )
    )

    request = client.create_stream.await_args.args[0]
    assert request.to_api() == {
        "campaign_id": 7,
        "name": "Geo US",
        "type": "regular",
        "schema": "redirect",
        "position": 1,
        "action_type": "http",
        "action_payload": "https://google.com",
        "filters": [{"name": "country", "mode": "accept", "payload": ["US"]}],
    }
    assert stream.id == 8
    assert stream.schema == "redirect"


@pytest.mark.asyncio
async def test_create_stream_sends_single_full_share_offer() -> None:
    client = AsyncMock(spec=KeitaroClient)
    client.create_stream.return_value = KeitaroStream.model_validate(
        {
            "id": 9,
            "campaign_id": 7,
            "schema": "landings",
            "offers": [{"offer_id": 5, "share": 100}],
        }
    )
    repository = KeitaroCampaignRepository(client)

    stream = await repository.create_stream(
        CreateStream(
            campaign_id=7,
            name="Offers",
            type="default",
            schema="landings",
            position=2,
            action_type="http",
            offers=({"offer_id": 5, "share": 100, "state": "active"},),
        )
    )

    request = client.create_stream.await_args.args[0]
    assert request.to_api()["type"] == "default"
    assert request.to_api()["schema"] == "landings"
    assert request.to_api()["position"] == 2
    assert request.to_api()["offers"] == [
        {"offer_id": 5, "share": 100, "state": "active"}
    ]
    assert "filters" not in request.to_api()
    assert [offer.offer_id for offer in stream.offers] == [5]


@pytest.mark.asyncio
async def test_list_streams_maps_keitaro_schemas_to_domain() -> None:
    client = AsyncMock(spec=KeitaroClient)
    client.list_streams.return_value = [
        KeitaroStream(id=8, campaign_id=7, schema="landings")
    ]
    repository = KeitaroCampaignRepository(client)

    streams = await repository.list_streams(7)

    assert streams == [
        Stream(
            id=8,
            campaign_id=7,
            schema="landings",
            raw_payload={"id": 8, "campaign_id": 7, "schema": "landings"},
        )
    ]


@pytest.mark.asyncio
async def test_update_stream_preserves_current_stream_settings() -> None:
    client = AsyncMock(spec=KeitaroClient)
    client.get_stream.return_value = KeitaroStream.model_validate(
        {
            "id": 8,
            "campaign_id": 7,
            "name": "Offers",
            "type": "default",
            "schema": "landings",
            "position": 2,
            "filters": [
                {"name": "country", "mode": "accept", "payload": ["US"]}
            ],
            "traffic_source_id": 17,
            "offers": [{"offer_id": 1, "share": 100}],
        }
    )
    client.update_stream.return_value = KeitaroStream.model_validate(
        {
            "id": 8,
            "campaign_id": 7,
            "schema": "landings",
            "filters": [
                {"name": "country", "mode": "accept", "payload": ["US"]}
            ],
            "traffic_source_id": 17,
            "offers": [{"offer_id": 2, "share": 100}],
        }
    )
    repository = KeitaroCampaignRepository(client)

    await repository.update_stream(
        8, [StreamOffer(offer_id=2, share=100, state="active")]
    )

    client.get_stream.assert_awaited_once_with(8)
    payload = client.update_stream.await_args.args[1]
    assert payload["filters"] == [
        {"name": "country", "mode": "accept", "payload": ["US"]}
    ]
    assert payload["traffic_source_id"] == 17
    assert payload["offers"] == [
        {"offer_id": 2, "share": 100, "state": "active"}
    ]
    assert "id" not in payload


@pytest.mark.asyncio
async def test_update_stream_reuses_an_already_read_stream() -> None:
    client = AsyncMock(spec=KeitaroClient)
    client.update_stream.return_value = KeitaroStream.model_validate(
        {
            "id": 8,
            "campaign_id": 7,
            "schema": "landings",
            "offers": [{"offer_id": 2, "share": 100}],
        }
    )
    repository = KeitaroCampaignRepository(client)
    current = Stream(
        id=8,
        campaign_id=7,
        name="Offers",
        schema="landings",
        raw_payload={
            "id": 8,
            "campaign_id": 7,
            "name": "Offers",
            "schema": "landings",
            "created_at": "2026-01-01T00:00:00Z",
            "offers": [{"offer_id": 1, "share": 100}],
        },
    )

    await repository.update_stream(
        8,
        [StreamOffer(offer_id=2, share=100, state="active")],
        current=current,
    )

    client.get_stream.assert_not_awaited()
    assert client.update_stream.await_args.args[1] == {
        "campaign_id": 7,
        "name": "Offers",
        "schema": "landings",
        "offers": [{"offer_id": 2, "share": 100, "state": "active"}],
    }
