from unittest.mock import AsyncMock

import pytest

from app.application.campaigns.creator import CampaignCreator
from app.application.campaigns.dtos import CampaignDefaults, CreateCampaign
from app.application.campaigns.streams import CampaignStreamsCreator
from app.application.errors import (
    ExternalServiceError,
    NotFoundError,
    RepositoryNotFoundError,
)
from app.domain.campaigns.entities import Campaign, Stream
from app.domain.catalog.entities import Offer


def build_creator() -> tuple[CampaignCreator, AsyncMock, AsyncMock, AsyncMock]:
    repository = AsyncMock()
    audit = AsyncMock()
    streams_creator = AsyncMock(spec=CampaignStreamsCreator)
    defaults = CampaignDefaults(
        domain_id=10,
        group_id=20,
        traffic_source_id=30,
    )
    creator = CampaignCreator(repository, audit, streams_creator, defaults)
    return creator, repository, audit, streams_creator


def stream(stream_id: int, position: int) -> Stream:
    return Stream(
        id=stream_id,
        campaign_id=7,
        name=f"stream-{position}",
        type="default",
        schema="landings",
        position=position,
    )


@pytest.mark.asyncio
async def test_create_uses_overrides_and_records_success() -> None:
    creator, repository, audit, streams_creator = build_creator()
    repository.get_offer.return_value = Offer(id=5, name="offer")
    campaign = Campaign(id=7, name="campaign")
    repository.create_campaign.return_value = campaign
    streams = [stream(11, 1), stream(12, 2)]
    streams_creator.create.return_value = streams

    result = await creator.create(
        name="campaign",
        alias="campaign-123456789abc",
        geo="US",
        offer_id=5,
        domain_id=100,
        group_id=200,
        source_id=300,
    )

    repository.create_campaign.assert_awaited_once_with(
        CreateCampaign(
            name="campaign",
            alias="campaign-123456789abc",
            domain_id=100,
            group_id=200,
            traffic_source_id=300,
        )
    )
    streams_creator.create.assert_awaited_once_with(7, geo="US", offer_id=5)
    assert audit.begin.await_args.kwargs["action"] == "campaign.create"
    assert audit.finish.await_args.kwargs["status"] == "ok"
    assert result == (campaign, streams)


@pytest.mark.asyncio
async def test_create_uses_configured_defaults() -> None:
    creator, repository, _, streams_creator = build_creator()
    repository.get_offer.return_value = Offer(id=5, name="offer")
    repository.create_campaign.return_value = Campaign(id=7, name="campaign")
    streams_creator.create.return_value = [stream(11, 1)]

    await creator.create(
        name="campaign",
        alias="campaign-123456789abc",
        geo="US",
        offer_id=5,
    )

    assert repository.create_campaign.await_args.args == (
        CreateCampaign(
            name="campaign",
            alias="campaign-123456789abc",
            domain_id=10,
            group_id=20,
            traffic_source_id=30,
        ),
    )


@pytest.mark.asyncio
async def test_create_maps_missing_offer_to_not_found() -> None:
    creator, repository, _, _ = build_creator()
    repository.get_offer.side_effect = RepositoryNotFoundError

    with pytest.raises(NotFoundError, match="#5"):
        await creator.create(
            name="campaign",
            alias="campaign-123456789abc",
            geo="US",
            offer_id=5,
        )

    repository.create_campaign.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_rolls_back_when_stream_setup_fails() -> None:
    creator, repository, audit, streams_creator = build_creator()
    repository.get_offer.return_value = Offer(id=5, name="offer")
    repository.create_campaign.return_value = Campaign(id=7, name="campaign")
    streams_creator.create.side_effect = ExternalServiceError(
        "stream setup failed"
    )

    with pytest.raises(ExternalServiceError, match="stream setup failed"):
        await creator.create(
            name="campaign",
            alias="campaign-123456789abc",
            geo="US",
            offer_id=5,
        )

    repository.delete_campaign.assert_awaited_once_with(7)
    assert audit.finish.await_args.kwargs["status"] == "rolled_back"


@pytest.mark.asyncio
async def test_create_records_failed_rollback() -> None:
    creator, repository, audit, streams_creator = build_creator()
    repository.get_offer.return_value = Offer(id=5, name="offer")
    repository.create_campaign.return_value = Campaign(id=7, name="campaign")
    streams_creator.create.side_effect = ExternalServiceError("setup failed")
    repository.delete_campaign.side_effect = ExternalServiceError(
        "delete failed"
    )

    with pytest.raises(ExternalServiceError, match="setup failed"):
        await creator.create(
            name="campaign",
            alias="campaign-123456789abc",
            geo="US",
            offer_id=5,
        )

    assert audit.finish.await_args.kwargs["status"] == "rollback_failed"
