"""Преобразование типов каталога Keitaro в доменные типы."""

from app.domain.catalog.entities import Offer, Reference
from app.infrastructure.keitaro.schemas import (
    CampaignGroup,
    Domain,
    TrafficSource,
)
from app.infrastructure.keitaro.schemas import (
    Offer as KeitaroOffer,
)


def offer_to_domain(offer: KeitaroOffer) -> Offer:
    return Offer(id=offer.id, name=offer.name)


def reference_to_domain(
    item: Domain | CampaignGroup | TrafficSource,
) -> Reference:
    return Reference(id=item.id, name=item.name)
