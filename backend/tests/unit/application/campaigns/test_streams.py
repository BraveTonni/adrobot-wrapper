from unittest.mock import AsyncMock

import pytest

from app.application.campaigns.dtos import CampaignStreamDefinition
from app.application.campaigns.streams import CampaignStreamsCreator
from app.application.errors import ExternalServiceError
from app.domain.campaigns.entities import Stream


def stream(stream_id: int, position: int) -> Stream:
    return Stream(
        id=stream_id,
        campaign_id=7,
        name=f"stream-{stream_id}",
        schema="landings" if position == 2 else "redirect",
        position=position,
    )


@pytest.mark.asyncio
async def test_create_builds_default_streams_and_interpolates_geo() -> None:
    repository = AsyncMock()
    geo_stream = stream(11, 1)
    offer_stream = stream(12, 2)
    repository.create_stream.side_effect = [geo_stream, offer_stream]
    repository.list_streams.return_value = [geo_stream, offer_stream]
    creator = CampaignStreamsCreator(
        repository, geo_redirect_url="https://redirect.example"
    )

    result = await creator.create(7, geo="US", offer_id=5)

    first, second = [
        call.args[0] for call in repository.create_stream.await_args_list
    ]
    assert first.name == "Geo US"
    assert first.schema == "redirect"
    assert first.action_payload == "https://redirect.example"
    assert first.filters == (
        {"name": "country", "mode": "accept", "payload": ["US"]},
    )
    assert second.schema == "landings"
    assert second.offers == ({"offer_id": 5, "share": 100, "state": "active"},)
    repository.list_streams.assert_awaited_once_with(7)
    assert result == [geo_stream, offer_stream]


@pytest.mark.asyncio
async def test_create_supports_an_arbitrary_configured_stream_set() -> None:
    repository = AsyncMock()
    definitions = [
        CampaignStreamDefinition(
            name="Fallback {geo}",
            type="forced",
            schema="redirect",
            position=3,
            action_payload="https://fallback.example/{geo}",
        ),
        CampaignStreamDefinition(
            name="Primary {geo}",
            type="regular",
            schema="redirect",
            position=1,
            filters=(
                {"name": "country", "mode": "accept", "payload": ["{geo}"]},
            ),
        ),
        CampaignStreamDefinition(
            name="Landings",
            type="default",
            schema="landings",
            position=2,
            initial_offer=True,
        ),
    ]
    created = [stream(11, 1), stream(12, 2), stream(13, 3)]
    repository.create_stream.side_effect = created
    repository.list_streams.return_value = created
    creator = CampaignStreamsCreator(repository, definitions)

    result = await creator.create(7, geo="CA", offer_id=5)

    commands = [
        call.args[0] for call in repository.create_stream.await_args_list
    ]
    assert [item.position for item in commands] == [1, 2, 3]
    assert [item.name for item in commands] == [
        "Primary CA",
        "Landings",
        "Fallback CA",
    ]
    assert commands[0].filters[0]["payload"] == ["CA"]
    assert commands[2].action_payload == "https://fallback.example/CA"
    assert result == created


@pytest.mark.asyncio
async def test_create_rejects_unexpected_stream_order() -> None:
    repository = AsyncMock()
    geo_stream = stream(11, 1)
    offer_stream = stream(12, 2)
    repository.create_stream.side_effect = [geo_stream, offer_stream]
    repository.list_streams.return_value = [offer_stream, geo_stream]
    creator = CampaignStreamsCreator(repository)

    with pytest.raises(ExternalServiceError, match="неожиданный порядок"):
        await creator.create(7, geo="US", offer_id=5)


def test_create_rejects_invalid_stream_definitions() -> None:
    repository = AsyncMock()
    with pytest.raises(ValueError, match="уникальны"):
        CampaignStreamsCreator(
            repository,
            [
                CampaignStreamDefinition("A", "regular", "redirect", 1),
                CampaignStreamDefinition(
                    "Offers", "default", "landings", 1, initial_offer=True
                ),
            ],
        )

    with pytest.raises(ValueError, match="начальным оффером"):
        CampaignStreamsCreator(
            repository,
            [CampaignStreamDefinition("Geo", "regular", "redirect", 1)],
        )
