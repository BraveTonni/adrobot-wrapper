import pytest

from app.domain.campaigns.entities import StreamOffer
from app.domain.campaigns.offer_state import (
    cancel_draft,
    has_draft,
    offers_for_push,
    restore_offer,
    soft_delete_offer,
)
from app.domain.shares import (
    distribute_shares,
    rebalance_active_offers,
    validate_offer_shares,
)


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        (0, []),
        (-1, []),
        (1, [100]),
        (2, [50, 50]),
        (3, [34, 33, 33]),
        (7, [15, 15, 14, 14, 14, 14, 14]),
        (6, [17, 17, 17, 17, 16, 16]),
        (100, [1] * 100),
    ],
)
def test_distributes_shares(count: int, expected: list[int]) -> None:
    assert distribute_shares(count) == expected


def test_rejects_more_than_one_hundred_offers() -> None:
    with pytest.raises(ValueError, match="100"):
        distribute_shares(101)


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        (0, []),
        (1, [100]),
        (2, [50, 50]),
        (3, [34, 33, 33]),
        (7, [15, 15, 14, 14, 14, 14, 14]),
        (100, [1] * 100),
    ],
)
def test_rebalances_boundary_offer_counts(
    count: int, expected: list[int]
) -> None:
    offers = [
        StreamOffer(offer_id=index + 1, share=1, state="active")
        for index in range(count)
    ]

    if count == 0:
        with pytest.raises(ValueError, match="хотя бы один"):
            rebalance_active_offers(offers)
        return

    assert [
        offer.share for offer in rebalance_active_offers(offers)
    ] == expected


def test_rebalance_keeps_pinned_share_and_distributes_the_remainder() -> None:
    offers = [
        StreamOffer(offer_id=1, share=40, state="active", is_pinned=True),
        StreamOffer(offer_id=2, share=20, state="active"),
        StreamOffer(offer_id=3, share=40, state="active"),
    ]

    result = rebalance_active_offers(offers)

    assert [offer.share for offer in result] == [40, 30, 30]
    assert result[0].is_pinned
    assert sum(offer.share for offer in result) == 100


def test_rebalance_rejects_unfillable_pinned_remainder() -> None:
    offers = [
        StreamOffer(offer_id=1, share=99, state="active", is_pinned=True),
        StreamOffer(offer_id=2, share=1, state="active"),
        StreamOffer(offer_id=3, share=1, state="active"),
    ]

    with pytest.raises(ValueError, match="недостаточно долей"):
        rebalance_active_offers(offers)


def test_rebalance_allows_pinned_offer_that_already_owns_all_shares() -> None:
    offers = [
        StreamOffer(offer_id=1, share=100, state="active", is_pinned=True)
    ]

    assert rebalance_active_offers(offers) == offers


def test_validate_push_requires_active_share_total_of_100_percent() -> None:
    with pytest.raises(ValueError, match="равна 100"):
        validate_offer_shares(
            [
                StreamOffer(offer_id=1, share=40, state="active"),
                StreamOffer(offer_id=2, share=40, state="active"),
            ]
        )


def test_validate_push_rejects_empty_offer_list() -> None:
    with pytest.raises(ValueError, match="хотя бы один оффер"):
        validate_offer_shares([])


def test_cancel_draft_restores_published_values() -> None:
    offer = StreamOffer(
        offer_id=1,
        share=70,
        state="active",
        published_share=100,
        published_state="active",
        draft_share=70,
        draft_state="active",
    )

    cancelled = cancel_draft([offer])[0]

    assert not has_draft(cancelled)
    assert cancelled.share == cancelled.published_share == 100
    assert cancelled.draft_share == 100


def test_soft_delete_can_be_cancelled_or_restored() -> None:
    offer = StreamOffer(offer_id=1, share=100, state="active")

    deleted = soft_delete_offer([offer], 1)[0]
    assert deleted.is_deleted and has_draft(deleted)
    assert offers_for_push([deleted, StreamOffer(offer_id=2, share=100)]) == [
        StreamOffer(offer_id=2, share=100)
    ]

    restored = restore_offer([deleted], 1)[0]
    assert not restored.is_deleted
    assert restored.state == "active"
    assert not has_draft(restored)

    cancelled = cancel_draft([deleted])[0]
    assert not cancelled.is_deleted
    assert cancelled.state == "active"


def test_deleted_offer_share_difference_is_not_an_unpublished_draft() -> None:
    offer = StreamOffer(
        offer_id=1,
        share=40,
        state="deleted",
        published_share=60,
        published_state="deleted",
        draft_share=40,
        draft_state="deleted",
        is_deleted=True,
    )

    assert not has_draft(offer)
