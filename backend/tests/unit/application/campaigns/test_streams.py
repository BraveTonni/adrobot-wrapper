from unittest.mock import AsyncMock

import pytest

from app.application.campaigns.streams import CampaignStreamsCreator
from app.application.errors import ExternalServiceError
from app.domain.campaigns.entities import Stream


def stream(stream_id: int) -> Stream:
    return Stream(
        id=stream_id,
        campaign_id=7,
        name=f"stream-{stream_id}",
        schema="redirect",
    )


@pytest.mark.asyncio
async def test_create_asks_repository_to_create_streams_in_order() -> None:
    repository = AsyncMock()
    geo_stream = stream(11)
    offer_stream = stream(12)
    repository.create_geo_stream.return_value = geo_stream
    repository.create_offer_stream.return_value = offer_stream
    repository.list_streams.return_value = [geo_stream, offer_stream]
    creator = CampaignStreamsCreator(repository)

    result = await creator.create(7, geo="US", offer_id=5)

    repository.create_geo_stream.assert_awaited_once_with(7, "US")
    repository.create_offer_stream.assert_awaited_once_with(7, 5)
    repository.list_streams.assert_awaited_once_with(7)
    assert result == [geo_stream, offer_stream]


@pytest.mark.asyncio
async def test_create_rejects_unexpected_stream_order() -> None:
    repository = AsyncMock()
    repository.create_geo_stream.return_value = stream(11)
    repository.create_offer_stream.return_value = stream(12)
    repository.list_streams.return_value = [stream(12), stream(11)]
    creator = CampaignStreamsCreator(repository)

    with pytest.raises(ExternalServiceError, match="неожиданный порядок"):
        await creator.create(7, geo="US", offer_id=5)
