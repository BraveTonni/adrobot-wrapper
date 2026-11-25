"""Application port for durable HTTP request deduplication."""

from typing import Protocol


class IdempotencyRepository(Protocol):
    async def reserve(
        self, key: str, request_hash: str
    ) -> tuple[str, dict[str, object] | None]: ...

    async def complete(
        self, key: str, response: dict[str, object]
    ) -> None: ...

    async def release(self, key: str) -> None: ...

    async def release_stale(self, key: str) -> bool: ...
