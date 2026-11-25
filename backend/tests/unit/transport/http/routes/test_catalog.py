from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.application.catalog.dtos import References
from app.domain.catalog.entities import Offer, Reference
from app.transport.http.routes.catalog import offers, references


@pytest.mark.asyncio
async def test_references_returns_each_reference_group() -> None:
    catalog = SimpleNamespace(
        references=AsyncMock(
            return_value=References(
                domains=[Reference(id=1, name="Domain")],
                groups=[Reference(id=2, name="Group")],
                sources=[Reference(id=3, name="Source")],
            )
        )
    )

    result = await references(catalog)

    assert result.model_dump() == {
        "domains": [{"id": 1, "name": "Domain"}],
        "groups": [{"id": 2, "name": "Group"}],
        "sources": [{"id": 3, "name": "Source"}],
    }


@pytest.mark.asyncio
async def test_offers_returns_catalog_results() -> None:
    catalog = SimpleNamespace(
        search_offers=AsyncMock(return_value=[Offer(id=4, name="Offer")])
    )

    result = await offers(catalog, search="off", limit=5)

    assert [item.model_dump() for item in result] == [
        {"id": 4, "name": "Offer"}
    ]
    catalog.search_offers.assert_awaited_once_with("off", 5)
