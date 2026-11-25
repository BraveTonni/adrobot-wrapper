from unittest.mock import AsyncMock

import pytest

from app.application.campaigns.queries import CampaignQueries
from app.domain.campaigns.entities import Campaign, Stream


@pytest.mark.asyncio
async def test_search_filters_campaign_names_case_insensitively() -> None:
    repository = AsyncMock()
    repository.list_campaigns.return_value = [
        Campaign(id=1, name="Spring"),
        Campaign(id=2, name="Winter"),
    ]
    queries = CampaignQueries(repository)

    result = await queries.search("SPR", 20)

    assert result == [Campaign(id=1, name="Spring")]
    repository.list_campaigns.assert_awaited_once_with(20, 0)


@pytest.mark.asyncio
async def test_get_with_streams_returns_campaign_and_streams() -> None:
    campaign = Campaign(id=1, name="Spring")
    streams = [Stream(id=2, campaign_id=1)]
    repository = AsyncMock()
    repository.get_campaign.return_value = campaign
    repository.list_streams.return_value = streams
    queries = CampaignQueries(repository)

    result = await queries.get_with_streams(1)

    assert result == (campaign, streams)
    repository.list_streams.assert_awaited_once_with(1)
