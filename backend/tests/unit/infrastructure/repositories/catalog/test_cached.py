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


@pytest.fixture
async def session_factory():
    """Пустая база в памяти под хранилище кэша."""
    engine = build_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = build_session_factory(engine)
    try:
        yield factory
    finally:
        await engine.dispose()


def build_cache(
    session_factory, repository: AsyncMock | None = None, *, ttl: float = 60
) -> CachedCatalogRepository:
    return CachedCatalogRepository(
        repository or AsyncMock(),
        offers_ttl=ttl,
        references_ttl=ttl,
        session_factory=session_factory,
    )


@pytest.mark.asyncio
async def test_cached_repository_reuses_offer_results(session_factory) -> None:
    repository = AsyncMock()
    repository.list_offers.return_value = [Offer(id=5, name="Offer")]
    cached = build_cache(session_factory, repository)

    first = await cached.list_offers()
    second = await cached.list_offers()

    assert first == second == [Offer(id=5, name="Offer")]
    repository.list_offers.assert_awaited_once()


@pytest.mark.asyncio
async def test_cached_repository_reuses_reference_results(
    session_factory,
) -> None:
    references = References(
        domains=[Reference(id=1, name="domain")],
        groups=[],
        sources=[],
    )
    repository = AsyncMock()
    repository.list_references.return_value = references
    cached = build_cache(session_factory, repository)

    first = await cached.list_references()
    second = await cached.list_references()

    assert first == second == references
    repository.list_references.assert_awaited_once()


@pytest.mark.asyncio
async def test_persistent_cache_survives_instances_and_manual_refresh(
    session_factory,
) -> None:
    repository = AsyncMock()
    repository.list_offers.side_effect = [
        [Offer(id=1, name="Old")],
        [Offer(id=2, name="New")],
    ]
    repository.list_references.return_value = References([], [], [])
    cached = build_cache(session_factory, repository, ttl=300)

    assert await cached.list_offers() == [Offer(id=1, name="Old")]
    await cached.refresh()

    fresh_instance = build_cache(session_factory, AsyncMock(), ttl=300)
    assert await fresh_instance.list_offers() == [Offer(id=2, name="New")]
    assert repository.list_offers.await_count == 2


@pytest.mark.asyncio
async def test_persistent_cache_reload_occurs_after_ttl_expiration(
    session_factory,
) -> None:
    from datetime import UTC, datetime, timedelta

    repository = AsyncMock()
    repository.list_offers.side_effect = [
        [Offer(id=1, name="Old")],
        [Offer(id=2, name="Fresh")],
    ]
    cached = build_cache(session_factory, repository, ttl=300)
    await cached.list_offers()

    async with session_factory() as session:
        entry = await session.get(CatalogCacheEntry, "offers")
        assert entry is not None
        entry.updated_at = datetime.now(UTC) - timedelta(minutes=10)
        await session.commit()

    assert await cached.list_offers() == [Offer(id=2, name="Fresh")]
    assert repository.list_offers.await_count == 2
