from unittest.mock import AsyncMock

import pytest

from app.application.campaigns.editor import CampaignEditor
from app.application.errors import (
    ConflictError,
    NotFoundError,
    RepositoryNotFoundError,
)
from app.domain.campaigns.entities import Stream, StreamOffer
from app.domain.catalog.entities import Offer


def build_editor() -> tuple[CampaignEditor, AsyncMock, AsyncMock]:
    repository = AsyncMock()
    audit = AsyncMock()
    return CampaignEditor(repository, audit), repository, audit


def offer_stream(offers: list[StreamOffer] | None = None) -> Stream:
    return Stream(
        id=11,
        campaign_id=7,
        name="Offers",
        type="default",
        schema="landings",
        offers=offers or [],
    )


@pytest.mark.asyncio
async def test_add_offer_preserves_metadata_and_recalculates_shares() -> None:
    editor, repository, audit = build_editor()
    repository.get_offer.return_value = Offer(id=2, name="Offer")
    repository.get_stream.return_value = offer_stream(
        [
            StreamOffer(
                offer_id=1,
                share=100,
                state="active",
                metadata={"custom": "keep"},
            )
        ]
    )
    updated_stream = offer_stream(
        [
            StreamOffer(
                offer_id=1,
                share=50,
                state="active",
                metadata={"custom": "keep"},
            ),
            StreamOffer(offer_id=2, share=50, state="active"),
        ]
    )
    repository.update_stream.return_value = updated_stream

    updated = await editor.add_offer(7, 11, 2)

    repository.get_offer.assert_awaited_once_with(2)
    repository.get_stream.assert_awaited_once_with(11)
    repository.update_stream.assert_awaited_once_with(
        11,
        [
            StreamOffer(
                offer_id=1,
                share=50,
                state="active",
                metadata={"custom": "keep"},
            ),
            StreamOffer(offer_id=2, share=50, state="active"),
        ],
    )
    assert sum(item.share for item in updated.offers) == 100
    assert audit.record.await_args.kwargs["action"] == "stream.offer_add"


@pytest.mark.asyncio
async def test_add_offer_rejects_existing_offer() -> None:
    editor, repository, _ = build_editor()
    repository.get_offer.return_value = Offer(id=2, name="Offer")
    repository.get_stream.return_value = offer_stream(
        [StreamOffer(offer_id=2)]
    )

    with pytest.raises(ConflictError, match="уже есть"):
        await editor.add_offer(7, 11, 2)

    repository.update_stream.assert_not_awaited()


@pytest.mark.asyncio
async def test_add_offer_maps_missing_offer() -> None:
    editor, repository, _ = build_editor()
    repository.get_offer.side_effect = RepositoryNotFoundError

    with pytest.raises(NotFoundError, match="#2"):
        await editor.add_offer(7, 11, 2)

    repository.get_stream.assert_not_awaited()


@pytest.mark.asyncio
async def test_remove_offer_recalculates_remaining_shares() -> None:
    editor, repository, audit = build_editor()
    repository.get_stream.return_value = offer_stream(
        [
            StreamOffer(offer_id=1, share=34),
            StreamOffer(offer_id=2, share=33),
            StreamOffer(offer_id=3, share=33),
        ]
    )
    repository.update_stream.return_value = offer_stream(
        [StreamOffer(offer_id=1, share=50), StreamOffer(offer_id=3, share=50)]
    )

    updated = await editor.remove_offer(7, 11, 2)

    assert [item.offer_id for item in updated.offers] == [1, 3]
    assert [item.share for item in updated.offers] == [50, 50]
    assert audit.record.await_args.kwargs["action"] == "stream.offer_remove"


@pytest.mark.asyncio
async def test_remove_offer_rejects_missing_offer() -> None:
    editor, repository, _ = build_editor()
    repository.get_stream.return_value = offer_stream(
        [StreamOffer(offer_id=1)]
    )

    with pytest.raises(NotFoundError, match="#2"):
        await editor.remove_offer(7, 11, 2)

    repository.update_stream.assert_not_awaited()


@pytest.mark.asyncio
async def test_remove_offer_rejects_removing_last_offer() -> None:
    editor, repository, _ = build_editor()
    repository.get_stream.return_value = offer_stream(
        [StreamOffer(offer_id=1)]
    )

    with pytest.raises(ConflictError, match="последний оффер"):
        await editor.remove_offer(7, 11, 1)

    repository.update_stream.assert_not_awaited()


@pytest.mark.asyncio
async def test_load_stream_rejects_stream_from_another_campaign() -> None:
    editor, repository, _ = build_editor()
    repository.get_stream.return_value = offer_stream()

    with pytest.raises(NotFoundError, match="не принадлежит"):
        await editor.remove_offer(8, 11, 1)


@pytest.mark.asyncio
async def test_load_stream_rejects_stream_without_offer_schema() -> None:
    editor, repository, _ = build_editor()
    repository.get_stream.return_value = Stream(
        id=11, campaign_id=7, name="Geo", schema="redirect"
    )
    with pytest.raises(ConflictError, match="не редактирует офферы"):
        await editor.remove_offer(7, 11, 1)


@pytest.mark.asyncio
async def test_load_stream_maps_repository_not_found() -> None:
    editor, repository, _ = build_editor()
    repository.get_stream.side_effect = RepositoryNotFoundError

    with pytest.raises(NotFoundError, match="Поток #11"):
        await editor.remove_offer(7, 11, 1)
