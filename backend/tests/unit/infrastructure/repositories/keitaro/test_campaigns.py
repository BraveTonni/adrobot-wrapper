from unittest.mock import AsyncMock

import pytest

from app.application.campaigns.dtos import CreateCampaign
from app.domain.campaigns.entities import Campaign, StreamOffer
from app.infrastructure.keitaro.client import KeitaroClient
from app.infrastructure.keitaro.schemas import Campaign as KeitaroCampaign
from app.infrastructure.repositories.keitaro.campaigns import (
    KeitaroCampaignRepository,
)


@pytest.mark.asyncio
async def test_create_campaign_maps_command_and_response() -> None:
    client = AsyncMock(spec=KeitaroClient)
    client.create_campaign.return_value = KeitaroCampaign(
        id=7, name="Launch", alias="launch"
    )
    repository = KeitaroCampaignRepository(client, "https://go.example")
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
async def test_list_streams_maps_keitaro_schemas_to_domain() -> None:
    from app.domain.campaigns.entities import Stream
    from app.infrastructure.keitaro.schemas import Stream as KeitaroStream

    client = AsyncMock(spec=KeitaroClient)
    client.list_streams.return_value = [
        KeitaroStream(id=8, campaign_id=7, schema="landings")
    ]
    repository = KeitaroCampaignRepository(client, "https://go.example")

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
    from app.infrastructure.keitaro.schemas import Stream as KeitaroStream

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
    repository = KeitaroCampaignRepository(client, "https://go.example")

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
