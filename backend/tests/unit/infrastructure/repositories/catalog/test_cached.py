from unittest.mock import AsyncMock

import pytest

from app.application.catalog.dtos import References
from app.domain.catalog.entities import Offer, Reference
from app.infrastructure.persistence.database import (
    build_engine,
    build_session_factory,
)
from app.infrastructure.persistence.models import Base
from app.infrastructure.persistence.models.catalog_cache import (
    CatalogCacheEntry,
)
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


@pytest.mark.asyncio
async def test_persistent_cache_survives_instances_and_manual_refresh() -> (
    None
):
    engine = build_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = build_session_factory(engine)
    repository = AsyncMock()
    repository.list_offers.side_effect = [
        [Offer(id=1, name="Old")],
        [Offer(id=2, name="New")],
    ]
    repository.list_references.return_value = References([], [], [])
    cached = CachedCatalogRepository(
        repository,
        offers_ttl=300,
        references_ttl=300,
        session_factory=factory,
    )

    assert await cached.list_offers() == [Offer(id=1, name="Old")]
    await cached.refresh()

    fresh_instance = CachedCatalogRepository(
        AsyncMock(),
        offers_ttl=300,
        references_ttl=300,
        session_factory=factory,
    )
    assert await fresh_instance.list_offers() == [Offer(id=2, name="New")]
    assert repository.list_offers.await_count == 2
    await engine.dispose()


@pytest.mark.asyncio
async def test_persistent_cache_reload_occurs_after_ttl_expiration() -> None:
    from datetime import UTC, datetime, timedelta

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    engine = build_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory: async_sessionmaker[AsyncSession] = build_session_factory(engine)
    repository = AsyncMock()
    repository.list_offers.side_effect = [
        [Offer(id=1, name="Old")],
        [Offer(id=2, name="Fresh")],
    ]
    cached = CachedCatalogRepository(
        repository,
        offers_ttl=300,
        references_ttl=300,
        session_factory=factory,
    )
    await cached.list_offers()

    async with factory() as session:
        entry = await session.get(CatalogCacheEntry, "offers")
        assert entry is not None
        entry.updated_at = datetime.now(UTC) - timedelta(minutes=10)
        await session.commit()

    assert await cached.list_offers() == [Offer(id=2, name="Fresh")]
    assert repository.list_offers.await_count == 2
    await engine.dispose()
