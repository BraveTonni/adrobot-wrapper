from app.application.campaigns.dtos import CreateCampaign
from app.infrastructure.keitaro.mappers.campaigns import (
    campaign_create_to_keitaro,
    campaign_to_domain,
)
from app.infrastructure.keitaro.schemas import Campaign as KeitaroCampaign


def test_campaign_response_maps_to_domain_entity() -> None:
    response = KeitaroCampaign(
        id=3,
        name="Launch",
        alias="launch",
        domain_id=10,
    )

    campaign = campaign_to_domain(response)

    assert campaign.id == 3
    assert campaign.alias == "launch"
    assert campaign.domain_id == 10


def test_campaign_command_maps_to_keitaro_request() -> None:
    command = CreateCampaign(
        name="Launch",
        alias="launch-123456789abc",
        domain_id=10,
        group_id=20,
        traffic_source_id=30,
    )

    request = campaign_create_to_keitaro(command)

    assert request.to_api() == {
        "name": "Launch",
        "alias": "launch-123456789abc",
        "type": "position",
        "domain_id": 10,
        "group_id": 20,
        "traffic_source_id": 30,
    }
