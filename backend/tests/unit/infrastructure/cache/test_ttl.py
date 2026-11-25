import asyncio
from unittest.mock import AsyncMock

import pytest

from app.infrastructure.cache.ttl import TTLCache


@pytest.mark.asyncio
async def test_cache_loads_once_until_expiry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = [10.0]
    monkeypatch.setattr(
        "app.infrastructure.cache.ttl.time.monotonic", lambda: clock[0]
    )
    cache: TTLCache[str] = TTLCache(ttl=5)
    calls = 0

    async def loader() -> str:
        nonlocal calls
        calls += 1
        return f"value-{calls}"

    assert await cache.get(loader) == "value-1"
    assert await cache.get(loader) == "value-1"
    clock[0] = 16.0
    assert await cache.get(loader) == "value-2"
    assert calls == 2


@pytest.mark.asyncio
async def test_concurrent_cache_misses_share_one_load() -> None:
    cache: TTLCache[str] = TTLCache(ttl=10)
    loader = AsyncMock(return_value="loaded")

    results = await asyncio.gather(*(cache.get(loader) for _ in range(8)))

    assert results == ["loaded"] * 8
    loader.assert_awaited_once()


@pytest.mark.asyncio
async def test_failed_load_is_not_cached() -> None:
    cache: TTLCache[str] = TTLCache(ttl=10)
    loader = AsyncMock(side_effect=[RuntimeError("temporary"), "ok"])

    with pytest.raises(RuntimeError, match="temporary"):
        await cache.get(loader)
    assert await cache.get(loader) == "ok"
    assert loader.await_count == 2
