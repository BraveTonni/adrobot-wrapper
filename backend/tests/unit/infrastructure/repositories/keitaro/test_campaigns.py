from unittest.mock import AsyncMock

import pytest

from app.application.campaigns.dtos import CreateCampaign
from app.domain.campaigns.entities import Campaign
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

    assert streams == [Stream(id=8, campaign_id=7, schema="landings")]
