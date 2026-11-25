from unittest.mock import AsyncMock

import pytest

from app.application.catalog.dtos import References
from app.application.catalog.service import Catalog
from app.domain.catalog.entities import Offer, Reference


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("query", "limit", "expected_ids"),
    [("BET", 5, [23]), ("34", 1, [34]), ("", 2, [12, 23])],
)
async def test_search_offers_filters_and_limits_results(
    query: str, limit: int, expected_ids: list[int]
) -> None:
    repository = AsyncMock()
    repository.list_offers.return_value = [
        Offer(id=12, name="Alpha"),
        Offer(id=23, name="Beta"),
        Offer(id=34, name="Gamma"),
    ]
    catalog = Catalog(repository)

    result = await catalog.search_offers(query, limit)

    assert [offer.id for offer in result] == expected_ids
    repository.list_offers.assert_awaited_once()


@pytest.mark.asyncio
async def test_references_returns_repository_result() -> None:
    references = References(
        domains=[Reference(id=1, name="domain")],
        groups=[Reference(id=2, name="group")],
        sources=[Reference(id=3, name="source")],
    )
    repository = AsyncMock()
    repository.list_references.return_value = references
    catalog = Catalog(repository)

    result = await catalog.references()

    assert result is references
    repository.list_references.assert_awaited_once()
