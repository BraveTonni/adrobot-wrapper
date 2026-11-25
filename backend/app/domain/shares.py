from dataclasses import replace

from app.domain.campaigns.entities import StreamOffer


def distribute_shares(count: int, total: int = 100) -> list[int]:
    """Равномерно распределяет total между count офферами."""
    if count <= 0:
        return []
    if count > 100:
        raise ValueError("больше 100 офферов в потоке нельзя")
    if total < count or total > 100:
        raise ValueError("недостаточно долей для активных офферов")
    base, rest = divmod(total, count)
    return [base + (1 if i < rest else 0) for i in range(count)]


def is_active_offer(offer: StreamOffer) -> bool:
    return not offer.is_deleted and (
        offer.state is None or offer.state.lower() == "active"
    )


def rebalance_active_offers(offers: list[StreamOffer]) -> list[StreamOffer]:
    active_indexes = [
        index for index, offer in enumerate(offers) if is_active_offer(offer)
    ]
    updated = list(offers)
    pinned_indexes = [
        index for index in active_indexes if offers[index].is_pinned
    ]
    movable_indexes = [
        index for index in active_indexes if not offers[index].is_pinned
    ]
    pinned_share = sum(offers[index].share for index in pinned_indexes)
    if pinned_share > 100:
        raise ValueError("сумма закреплённых долей не может превышать 100")
    if not movable_indexes and pinned_share != 100:
        raise ValueError("закреплённые активные офферы должны составлять 100%")
    shares = distribute_shares(len(movable_indexes), 100 - pinned_share)
    for index, share in zip(movable_indexes, shares, strict=True):
        updated[index] = replace(
            updated[index], share=share, draft_share=share
        )
    validate_offer_shares(updated)
    return updated


def validate_offer_shares(offers: list[StreamOffer]) -> None:
    if not offers:
        raise ValueError("поток должен содержать хотя бы один оффер")
    if any(not 1 <= offer.share <= 100 for offer in offers):
        raise ValueError("доля каждого оффера должна быть в диапазоне 1–100")

    active = [offer for offer in offers if is_active_offer(offer)]
    if not active:
        raise ValueError("для push нужен хотя бы один активный оффер")
    if sum(offer.share for offer in active) != 100:
        raise ValueError("сумма долей активных офферов должна быть равна 100")
