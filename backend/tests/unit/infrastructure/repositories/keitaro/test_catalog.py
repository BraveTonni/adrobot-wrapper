from unittest.mock import AsyncMock

import pytest

from app.application.catalog.dtos import References
from app.domain.catalog.entities import Offer, Reference
from app.infrastructure.keitaro.client import KeitaroClient
from app.infrastructure.keitaro.schemas import (
    CampaignGroup,
    Domain,
    TrafficSource,
)
from app.infrastructure.keitaro.schemas import (
    Offer as KeitaroOffer,
)
from app.infrastructure.repositories.keitaro.catalog import (
    KeitaroCatalogRepository,
)


@pytest.mark.asyncio
async def test_list_offers_maps_external_models_to_domain() -> None:
    client = AsyncMock(spec=KeitaroClient)
    client.list_offers.return_value = [KeitaroOffer(id=5, name="Offer")]
    repository = KeitaroCatalogRepository(client)

    result = await repository.list_offers()

    assert result == [Offer(id=5, name="Offer")]


@pytest.mark.asyncio
async def test_list_references_maps_each_external_reference_type() -> None:
    client = AsyncMock(spec=KeitaroClient)
    client.list_domains.return_value = [Domain(id=1, name="domain")]
    client.list_groups.return_value = [CampaignGroup(id=2, name="group")]
    client.list_sources.return_value = [TrafficSource(id=3, name="source")]
    repository = KeitaroCatalogRepository(client)

    result = await repository.list_references()

    assert result == References(
        domains=[Reference(id=1, name="domain")],
        groups=[Reference(id=2, name="group")],
        sources=[Reference(id=3, name="source")],
    )
    client.list_domains.assert_awaited_once()
    client.list_groups.assert_awaited_once()
    client.list_sources.assert_awaited_once()
