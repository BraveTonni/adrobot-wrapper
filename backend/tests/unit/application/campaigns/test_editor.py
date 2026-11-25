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


def build_draft_editor() -> tuple[
    CampaignEditor, AsyncMock, AsyncMock, AsyncMock
]:
    repository = AsyncMock()
    audit = AsyncMock()
    drafts = AsyncMock()
    return (
        CampaignEditor(repository, audit, drafts=drafts),
        repository,
        audit,
        drafts,
    )


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
                published_share=100,
                draft_share=50,
            ),
            StreamOffer(
                offer_id=2,
                share=50,
                state="active",
                published_state="deleted",
                published_share=0,
                draft_share=50,
            ),
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
                published_share=100,
                draft_share=50,
            ),
            StreamOffer(
                offer_id=2,
                share=50,
                state="active",
                published_state="deleted",
                published_share=0,
                draft_share=50,
            ),
        ],
    )
    assert sum(item.share for item in updated.offers) == 100
    assert audit.begin.await_args.kwargs["action"] == "stream.offer_add"


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
    assert audit.begin.await_args.kwargs["action"] == "stream.offer_remove"


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


@pytest.mark.asyncio
async def test_push_omits_soft_deleted_offers_and_validates_active_sum() -> (
    None
):
    editor, repository, _ = build_editor()
    stream = offer_stream(
        [
            StreamOffer(offer_id=1, share=50, state="active"),
            StreamOffer(
                offer_id=2,
                share=50,
                state="deleted",
                is_deleted=True,
            ),
        ]
    )
    repository.update_stream.return_value = offer_stream(
        [StreamOffer(offer_id=1, share=100, state="active")]
    )

    await editor._save(stream, stream.offers, action="stream.sync")

    repository.update_stream.assert_awaited_once_with(
        11,
        [
            StreamOffer(
                offer_id=1,
                share=100,
                state="active",
                published_share=50,
                draft_share=100,
            )
        ],
    )


@pytest.mark.asyncio
async def test_draft_add_does_not_update_keitaro_until_push() -> None:
    editor, repository, _, drafts = build_draft_editor()
    repository.get_offer.return_value = Offer(id=2, name="Offer")
    drafts.get_stream.return_value = offer_stream(
        [StreamOffer(offer_id=1, share=100, state="active")]
    )

    updated = await editor.add_offer(7, 11, 2)

    assert [offer.share for offer in updated.offers] == [50, 50]
    assert updated.offers[1].published_state == "deleted"
    assert updated.offers[1].published_share == 0
    drafts.save_offers.assert_awaited_once_with(11, updated.offers)
    repository.update_stream.assert_not_awaited()


@pytest.mark.asyncio
async def test_draft_remove_allows_empty_active_set_and_can_be_cancelled() -> (
    None
):
    editor, repository, _, drafts = build_draft_editor()
    drafts.get_stream.return_value = offer_stream(
        [StreamOffer(offer_id=1, share=100, state="active")]
    )

    deleted = await editor.remove_offer(7, 11, 1)

    assert len(deleted.offers) == 1
    assert deleted.offers[0].is_deleted
    repository.update_stream.assert_not_awaited()


@pytest.mark.asyncio
async def test_push_publishes_local_draft_and_omits_soft_deleted_offers() -> (
    None
):
    editor, repository, _, drafts = build_draft_editor()
    draft = offer_stream(
        [
            StreamOffer(
                offer_id=1,
                share=100,
                state="active",
                published_share=50,
                draft_share=100,
            ),
            StreamOffer(
                offer_id=2,
                share=50,
                state="deleted",
                is_deleted=True,
            ),
        ]
    )
    published = offer_stream(
        [StreamOffer(offer_id=1, share=100, state="active")]
    )
    drafts.get_stream.side_effect = [draft, published]
    repository.update_stream.return_value = published

    result = await editor.push(7, 11)

    repository.update_stream.assert_awaited_once_with(
        11,
        [
            StreamOffer(
                offer_id=1,
                share=100,
                state="active",
                published_share=50,
                draft_share=100,
            )
        ],
    )
    drafts.sync_stream.assert_awaited_once_with(published)
    assert result.offers == published.offers


@pytest.mark.asyncio
async def test_push_rejects_empty_active_set_before_keitaro_request() -> None:
    editor, repository, _, drafts = build_draft_editor()
    drafts.get_stream.return_value = offer_stream(
        [
            StreamOffer(
                offer_id=1,
                share=100,
                state="deleted",
                is_deleted=True,
            )
        ]
    )

    with pytest.raises(ConflictError, match="хотя бы один оффер"):
        await editor.push(7, 11)

    repository.update_stream.assert_not_awaited()
    drafts.sync_stream.assert_not_awaited()


@pytest.mark.asyncio
async def test_cancel_draft_restores_and_discards_new_offer() -> None:
    editor, _, _, drafts = build_draft_editor()
    drafts.get_stream.return_value = offer_stream(
        [
            StreamOffer(
                offer_id=1,
                share=100,
                state="deleted",
                published_share=100,
                published_state="active",
                draft_share=100,
                draft_state="deleted",
                is_deleted=True,
            ),
            StreamOffer(
                offer_id=2,
                share=100,
                state="active",
                published_share=0,
                published_state="deleted",
                draft_share=100,
                draft_state="active",
            ),
        ]
    )

    updated = await editor.cancel_draft(7, 11)

    assert len(updated.offers) == 1
    assert updated.offers[0].offer_id == 1
    assert updated.offers[0].state == "active"
    assert not updated.offers[0].is_deleted
    drafts.save_offers.assert_awaited_once_with(11, updated.offers)
