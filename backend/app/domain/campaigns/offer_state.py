"""Pure helpers for published and draft offer state transitions."""

from dataclasses import replace
from typing import cast

from app.domain.campaigns.entities import StreamOffer
from app.domain.shares import validate_offer_shares


def has_draft(offer: StreamOffer) -> bool:
    deleted_in_both_states = (
        offer.is_deleted
        and offer.draft_state == "deleted"
        and offer.published_state == "deleted"
    )
    return (
        offer.draft_state != offer.published_state
        or (
            not deleted_in_both_states
            and offer.draft_share != offer.published_share
        )
        or offer.is_deleted != (offer.published_state == "deleted")
    )


def cancel_draft(offers: list[StreamOffer]) -> list[StreamOffer]:
    return [
        replace(
            offer,
            state=offer.published_state,
            share=cast(int, offer.published_share),
            draft_state=offer.published_state,
            draft_share=offer.published_share,
            is_deleted=offer.published_state == "deleted",
        )
        for offer in offers
        # A zero published share marks an offer created only in the local
        # draft. Cancelling that draft should discard the row entirely.
        if not (
            offer.published_state == "deleted" and offer.published_share == 0
        )
    ]


def soft_delete_offer(
    offers: list[StreamOffer], offer_id: int
) -> list[StreamOffer]:
    found = False
    updated: list[StreamOffer] = []
    for offer in offers:
        if offer.offer_id == offer_id:
            found = True
            updated.append(
                replace(
                    offer,
                    state="deleted",
                    draft_state="deleted",
                    is_deleted=True,
                )
            )
        else:
            updated.append(offer)
    if not found:
        raise ValueError(f"оффер #{offer_id} не найден")
    return updated


def restore_offer(
    offers: list[StreamOffer], offer_id: int
) -> list[StreamOffer]:
    found = False
    updated: list[StreamOffer] = []
    for offer in offers:
        if offer.offer_id == offer_id:
            found = True
            if not offer.is_deleted:
                raise ValueError(f"оффер #{offer_id} не удалён")
            state = (
                "active"
                if offer.published_state == "deleted"
                else offer.published_state
            )
            updated.append(
                replace(
                    offer,
                    state=state,
                    draft_state=state,
                    is_deleted=False,
                )
            )
        else:
            updated.append(offer)
    if not found:
        raise ValueError(f"оффер #{offer_id} не найден")
    return updated


def offers_for_push(offers: list[StreamOffer]) -> list[StreamOffer]:
    active = [offer for offer in offers if not offer.is_deleted]
    validate_offer_shares(active)
    return active
