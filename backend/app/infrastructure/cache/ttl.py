"""Кэш значения с TTL."""

import asyncio
import time
from collections.abc import Awaitable, Callable


class TTLCache[T]:
    """Ленивое значение; параллельные запросы ждут один результат."""

    def __init__(self, ttl: float) -> None:
        self._ttl = ttl
        self._value: T | None = None
        self._expires_at = 0.0
        self._lock = asyncio.Lock()

    async def get(self, loader: Callable[[], Awaitable[T]]) -> T:
        if self._value is not None and time.monotonic() < self._expires_at:
            return self._value
        async with self._lock:
            if self._value is not None and time.monotonic() < self._expires_at:
                return self._value
            self._value = await loader()
            self._expires_at = time.monotonic() + self._ttl
        return self._value

    async def refresh(self, loader: Callable[[], Awaitable[T]]) -> T:
        async with self._lock:
            self._value = await loader()
            self._expires_at = time.monotonic() + self._ttl
            return self._value
