import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.application.campaigns.creator import (
    CampaignCreator,
    CreationProgress,
)
from app.application.campaigns.dtos import CampaignDefaults, CreateCampaign
from app.application.campaigns.streams import CampaignStreamsCreator
from app.application.catalog.dtos import References
from app.application.errors import (
    ExternalServiceError,
    NotFoundError,
    RepositoryNotFoundError,
)
from app.domain.campaigns.entities import Campaign, Stream
from app.domain.catalog.entities import Offer, Reference


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


def create(**overrides: object) -> dict[str, object]:
    return {
        "name": "campaign",
        "alias": "campaign-123456789abc",
        "geo": "US",
        "offer_id": 5,
        **overrides,
    }


@pytest.mark.asyncio
async def test_create_uses_overrides_and_records_success() -> None:
    creator, repository, audit, streams_creator = build_creator()
    repository.get_offer.return_value = Offer(id=5, name="offer")
    campaign = Campaign(id=7, name="campaign")
    repository.create_campaign.return_value = campaign
    repository.get_campaign.return_value = campaign
    streams = [stream(11, 1), stream(12, 2)]
    streams_creator.create.return_value = streams

    result = await creator.create(
        **create(domain_id=100, group_id=200, source_id=300)
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
    assert (
        audit.finish.await_args.kwargs["after_payload"]["campaign"]["id"] == 7
    )
    assert result == (campaign, streams)


@pytest.mark.asyncio
async def test_create_uses_configured_defaults() -> None:
    creator, repository, _, streams_creator = build_creator()
    repository.get_offer.return_value = Offer(id=5, name="offer")
    campaign = Campaign(id=7, name="campaign")
    repository.create_campaign.return_value = campaign
    repository.get_campaign.return_value = campaign
    streams_creator.create.return_value = [stream(11, 1)]

    await creator.create(**create())

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
    creator, repository, audit, _ = build_creator()
    repository.get_offer.side_effect = RepositoryNotFoundError
    progress = CreationProgress()

    with pytest.raises(NotFoundError, match="#5"):
        await creator.create(**create(), progress=progress)

    repository.create_campaign.assert_not_awaited()
    assert progress.remote_state == "unchanged"
    assert audit.finish.await_args.kwargs["status"] == "failed"


@pytest.mark.parametrize(
    ("missing", "message"),
    [
        ("offer", "Оффер #5"),
        ("domain", "Домен #10"),
        ("group", "Группа кампаний #20"),
        ("source", "Источник трафика #30"),
    ],
)
@pytest.mark.asyncio
async def test_create_validates_catalog_before_remote_mutation(
    missing: str, message: str
) -> None:
    creator, repository, _, streams_creator = build_creator()
    offers = [] if missing == "offer" else [Offer(id=5, name="offer")]
    references = References(
        domains=[]
        if missing == "domain"
        else [Reference(id=10, name="Domain")],
        groups=[] if missing == "group" else [Reference(id=20, name="Group")],
        sources=[]
        if missing == "source"
        else [Reference(id=30, name="Source")],
    )
    creator._catalog = SimpleNamespace(
        offers=AsyncMock(return_value=offers),
        references=AsyncMock(return_value=references),
    )

    with pytest.raises(NotFoundError, match=message):
        await creator.create(**create())

    repository.create_campaign.assert_not_awaited()
    streams_creator.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_rolls_back_when_stream_setup_fails() -> None:
    creator, repository, audit, streams_creator = build_creator()
    repository.get_offer.return_value = Offer(id=5, name="offer")
    repository.create_campaign.return_value = Campaign(id=7, name="campaign")
    streams_creator.create.side_effect = ExternalServiceError(
        "stream setup failed"
    )
    progress = CreationProgress()

    with pytest.raises(ExternalServiceError, match="stream setup failed"):
        await creator.create(**create(), progress=progress)

    repository.delete_campaign.assert_awaited_once_with(7)
    assert audit.finish.await_args.kwargs["status"] == "rolled_back"
    assert progress.remote_state == "unchanged"


@pytest.mark.asyncio
async def test_create_records_failed_rollback() -> None:
    creator, repository, audit, streams_creator = build_creator()
    repository.get_offer.return_value = Offer(id=5, name="offer")
    repository.create_campaign.return_value = Campaign(id=7, name="campaign")
    streams_creator.create.side_effect = ExternalServiceError("setup failed")
    repository.delete_campaign.side_effect = ExternalServiceError(
        "delete failed"
    )
    progress = CreationProgress()

    with pytest.raises(ExternalServiceError, match="setup failed"):
        await creator.create(**create(), progress=progress)

    assert audit.finish.await_args.kwargs["status"] == "rollback_failed"
    assert "rollback failed" in audit.finish.await_args.kwargs["error"]
    assert progress.remote_state == "leftover"
    assert progress.campaign_id == 7


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    [
        # Ответ на запрос не получен: кампания могла создаться.
        ExternalServiceError("Keitaro недоступен"),
        ExternalServiceError("POST /campaigns -> HTTP 500", status=500),
    ],
)
async def test_create_reports_unknown_outcome_without_an_answer(
    failure: ExternalServiceError,
) -> None:
    creator, repository, audit, _ = build_creator()
    repository.get_offer.return_value = Offer(id=5, name="offer")
    repository.create_campaign.side_effect = failure
    progress = CreationProgress()

    with pytest.raises(ExternalServiceError):
        await creator.create(**create(), progress=progress)

    assert progress.remote_state == "unknown"
    assert audit.finish.await_args.kwargs["status"] == "unknown"
    repository.delete_campaign.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_reports_rejected_request_as_failed() -> None:
    creator, repository, audit, _ = build_creator()
    repository.get_offer.return_value = Offer(id=5, name="offer")
    repository.create_campaign.side_effect = ExternalServiceError(
        "POST /campaigns -> HTTP 400", status=400
    )
    progress = CreationProgress()

    with pytest.raises(ExternalServiceError, match="HTTP 400"):
        await creator.create(**create(), progress=progress)

    assert progress.remote_state == "unchanged"
    assert audit.finish.await_args.kwargs["status"] == "failed"
    repository.delete_campaign.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_records_cancelled_attempt_before_remote_write() -> None:
    creator, repository, audit, _ = build_creator()
    repository.get_offer.side_effect = asyncio.CancelledError()
    progress = CreationProgress()

    with pytest.raises(asyncio.CancelledError):
        await creator.create(**create(), progress=progress)

    assert audit.finish.await_args.kwargs["status"] == "cancelled"
    assert progress.remote_state == "unchanged"
    repository.create_campaign.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_verifies_campaign_before_saving_snapshot() -> None:
    creator, repository, _, streams_creator = build_creator()
    campaign = Campaign(id=7, name="campaign")
    repository.create_campaign.return_value = campaign
    repository.get_campaign.return_value = campaign
    streams_creator.create.return_value = [stream(11, 1)]
    snapshots = AsyncMock()
    creator._snapshots = snapshots

    await creator.create(**create())

    repository.get_campaign.assert_awaited_once_with(7)
    snapshots.save.assert_awaited_once_with(campaign, [stream(11, 1)])


@pytest.mark.asyncio
async def test_create_rolls_back_when_keitaro_returns_another_campaign() -> (
    None
):
    creator, repository, audit, streams_creator = build_creator()
    repository.create_campaign.return_value = Campaign(id=7, name="campaign")
    repository.get_campaign.return_value = Campaign(id=8, name="other")
    streams_creator.create.return_value = [stream(11, 1)]

    with pytest.raises(
        ExternalServiceError, match="вместо созданной кампании"
    ):
        await creator.create(**create())

    repository.delete_campaign.assert_awaited_once_with(7)
    assert audit.finish.await_args.kwargs["status"] == "rolled_back"


@pytest.mark.asyncio
async def test_create_keeps_campaign_when_keitaro_adjusts_fields() -> None:
    creator, repository, audit, streams_creator = build_creator()
    repository.create_campaign.return_value = Campaign(id=7, name="campaign")
    repository.get_campaign.return_value = Campaign(
        id=7,
        name="campaign ",
        alias="other-alias",
        domain_id=111,
        group_id=None,
        traffic_source_id=30,
    )
    streams_creator.create.return_value = [stream(11, 1)]
    progress = CreationProgress()

    await creator.create(**create(), progress=progress)

    repository.delete_campaign.assert_not_awaited()
    assert audit.finish.await_args.kwargs["status"] == "ok"
    assert audit.finish.await_args.kwargs["detail"]["warnings"] == (
        progress.warnings
    )
    assert any("название" in warning for warning in progress.warnings)
    assert any("алиас" in warning for warning in progress.warnings)
    assert any("домен" in warning for warning in progress.warnings)
    assert not any("источник" in warning for warning in progress.warnings)


@pytest.mark.asyncio
async def test_create_keeps_campaign_when_local_snapshot_cannot_be_saved() -> (
    None
):
    creator, repository, audit, streams_creator = build_creator()
    campaign = Campaign(id=7, name="campaign")
    repository.create_campaign.return_value = campaign
    repository.get_campaign.return_value = campaign
    streams_creator.create.return_value = [stream(11, 1)]
    snapshots = AsyncMock()
    snapshots.save.side_effect = RuntimeError("database unavailable")
    creator._snapshots = snapshots
    progress = CreationProgress()

    result = await creator.create(**create(), progress=progress)

    repository.delete_campaign.assert_not_awaited()
    assert result == (campaign, [stream(11, 1)])
    assert audit.finish.await_args.kwargs["status"] == "ok"
    assert any("снимок" in warning for warning in progress.warnings)
