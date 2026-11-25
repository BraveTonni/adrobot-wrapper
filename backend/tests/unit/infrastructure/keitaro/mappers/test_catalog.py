import pytest

from app.domain.catalog.entities import Offer, Reference
from app.infrastructure.keitaro.mappers.catalog import (
    offer_to_domain,
    reference_to_domain,
)
from app.infrastructure.keitaro.schemas import (
    CampaignGroup,
    Domain,
    TrafficSource,
)
from app.infrastructure.keitaro.schemas import (
    Offer as KeitaroOffer,
)


def test_offer_maps_to_domain_entity() -> None:
    assert offer_to_domain(KeitaroOffer(id=5, name="Offer")) == Offer(
        id=5, name="Offer"
    )


@pytest.mark.parametrize(
    "item",
    [
        Domain(id=1, name="domain"),
        CampaignGroup(id=2, name="group"),
        TrafficSource(id=3, name="source"),
    ],
)
def test_reference_models_map_to_one_domain_type(
    item: Domain | CampaignGroup | TrafficSource,
) -> None:
    result = reference_to_domain(item)

    assert result == Reference(id=item.id, name=item.name)
