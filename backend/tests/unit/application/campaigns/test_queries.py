from unittest.mock import AsyncMock

import pytest

from app.application.campaigns.queries import (
    SEARCH_PAGE_SIZE,
    SEARCH_SCAN_LIMIT,
    CampaignQueries,
)
from app.application.errors import NotFoundError, RepositoryNotFoundError
from app.domain.campaigns.entities import Campaign, Stream


def page(offset: int, size: int = SEARCH_PAGE_SIZE) -> list[Campaign]:
    return [
        Campaign(id=offset + index, name=f"Campaign {offset + index}")
        for index in range(size)
    ]


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
    repository.list_campaigns.assert_awaited_once_with(SEARCH_PAGE_SIZE, 0)


@pytest.mark.asyncio
async def test_search_scans_pages_until_the_last_one() -> None:
    repository = AsyncMock()
    repository.list_campaigns.side_effect = [
        page(0),
        page(100),
        [Campaign(id=200, name="Spring Opening")],
    ]
    queries = CampaignQueries(repository)

    result = await queries.search("spring opening", 20)

    assert [campaign.id for campaign in result] == [200]
    assert repository.list_campaigns.await_count == 3


@pytest.mark.asyncio
async def test_search_stops_at_the_scan_limit() -> None:
    repository = AsyncMock()
    repository.list_campaigns.side_effect = lambda limit, offset: page(offset)
    queries = CampaignQueries(repository)

    result = await queries.search("missing", 20)

    assert result == []
    assert repository.list_campaigns.await_count == (
        SEARCH_SCAN_LIMIT // SEARCH_PAGE_SIZE
    )


@pytest.mark.asyncio
async def test_numeric_search_opens_the_campaign_by_id() -> None:
    campaign = Campaign(id=42, name="Anything")
    repository = AsyncMock()
    repository.get_campaign.return_value = campaign
    queries = CampaignQueries(repository)

    assert await queries.search(" 42 ", 20) == [campaign]
    repository.get_campaign.assert_awaited_once_with(42)
    repository.list_campaigns.assert_not_awaited()


@pytest.mark.asyncio
async def test_numeric_search_reports_a_missing_campaign_as_empty() -> None:
    repository = AsyncMock()
    repository.get_campaign.side_effect = RepositoryNotFoundError
    queries = CampaignQueries(repository)

    assert await queries.search("42", 20) == []
    repository.list_campaigns.assert_not_awaited()


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


@pytest.mark.asyncio
async def test_get_with_streams_explains_missing_campaign() -> None:
    repository = AsyncMock()
    repository.get_campaign.side_effect = RepositoryNotFoundError
    queries = CampaignQueries(repository)

    with pytest.raises(NotFoundError, match="Кампания #9 не найдена"):
        await queries.get_with_streams(9)
    repository.list_streams.assert_not_awaited()
