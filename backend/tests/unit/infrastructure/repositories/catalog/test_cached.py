from unittest.mock import AsyncMock

import pytest

from app.application.catalog.dtos import References
from app.domain.catalog.entities import Offer, Reference
from app.infrastructure.repositories.catalog.cached import (
    CachedCatalogRepository,
)


@pytest.mark.asyncio
async def test_cached_repository_reuses_offer_results() -> None:
    repository = AsyncMock()
    offers = [Offer(id=5, name="Offer")]
    repository.list_offers.return_value = offers
    cached = CachedCatalogRepository(
        repository, offers_ttl=60, references_ttl=60
    )

    first = await cached.list_offers()
    second = await cached.list_offers()

    assert first is second
    repository.list_offers.assert_awaited_once()


@pytest.mark.asyncio
async def test_cached_repository_reuses_reference_results() -> None:
    repository = AsyncMock()
    references = References(
        domains=[Reference(id=1, name="domain")],
        groups=[],
        sources=[],
    )
    repository.list_references.return_value = references
    cached = CachedCatalogRepository(
        repository, offers_ttl=60, references_ttl=60
    )

    first = await cached.list_references()
    second = await cached.list_references()

    assert first is second
    repository.list_references.assert_awaited_once()
