from dataclasses import replace

from app.domain.campaigns.entities import StreamOffer


def distribute_shares(count: int) -> list[int]:
    """Доли в процентах: сумма всегда 100, разница не больше 1."""
    if count <= 0:
        return []
    if count > 100:
        raise ValueError("больше 100 офферов в потоке нельзя")
    base, rest = divmod(100, count)
    return [base + (1 if i < rest else 0) for i in range(count)]


def is_active_offer(offer: StreamOffer) -> bool:
    return offer.state is None or offer.state.lower() == "active"


def rebalance_active_offers(offers: list[StreamOffer]) -> list[StreamOffer]:
    active_indexes = [
        index for index, offer in enumerate(offers) if is_active_offer(offer)
    ]
    shares = distribute_shares(len(active_indexes))
    updated = list(offers)
    for index, share in zip(active_indexes, shares, strict=True):
        updated[index] = replace(updated[index], share=share)
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
