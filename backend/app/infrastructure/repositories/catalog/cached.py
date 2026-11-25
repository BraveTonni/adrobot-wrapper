"""Persistent TTL cache for the Keitaro catalog."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.catalog.dtos import References
from app.application.ports import CatalogReaderRepository
from app.domain.catalog.entities import Offer, Reference
from app.infrastructure.cache.ttl import TTLCache
from app.infrastructure.persistence.models.catalog_cache import (
    CatalogCacheEntry,
)


class CachedCatalogRepository:
    def __init__(
        self,
        repository: CatalogReaderRepository,
        *,
        offers_ttl: float,
        references_ttl: float,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._repository = repository
        self._session_factory = session_factory
        self._offers: TTLCache[list[Offer]] = TTLCache(offers_ttl)
        self._references: TTLCache[References] = TTLCache(references_ttl)
        self._locks = {
            "offers": asyncio.Lock(),
            "references": asyncio.Lock(),
        }
        self._database_write_lock = asyncio.Lock()
        self._ttls = {"offers": offers_ttl, "references": references_ttl}

    async def list_offers(self) -> list[Offer]:
        return await self._get("offers", self._repository.list_offers)

    async def list_references(self) -> References:
        return await self._get("references", self._repository.list_references)

    async def refresh(self) -> None:
        await asyncio.gather(
            self._get("offers", self._repository.list_offers, force=True),
            self._get(
                "references", self._repository.list_references, force=True
            ),
        )

    async def _get[T](
        self,
        key: str,
        loader: Callable[[], Awaitable[T]],
        *,
        force: bool = False,
    ) -> T:
        if self._session_factory is None:
            if key == "offers":
                offers_loader = cast(
                    Callable[[], Awaitable[list[Offer]]], loader
                )
                if force:
                    return cast(T, await self._offers.refresh(offers_loader))
                return cast(T, await self._offers.get(offers_loader))
            references_loader = cast(
                Callable[[], Awaitable[References]], loader
            )
            if force:
                return cast(
                    T, await self._references.refresh(references_loader)
                )
            return cast(T, await self._references.get(references_loader))

        async with self._locks[key]:
            async with self._session_factory() as session:
                entry = await session.get(CatalogCacheEntry, key)
                if (
                    not force
                    and entry is not None
                    and self._is_fresh(entry.updated_at, self._ttls[key])
                ):
                    return cast(T, _decode(key, entry.payload))

            value = await loader()
            payload = _encode(key, value)
            async with self._database_write_lock:
                async with self._session_factory() as session:
                    entry = await session.get(CatalogCacheEntry, key)
                    if entry is None:
                        entry = CatalogCacheEntry(key=key, payload=payload)
                        session.add(entry)
                    else:
                        entry.payload = payload
                        entry.updated_at = datetime.now(UTC)
                    await session.commit()
            return value

    @staticmethod
    def _is_fresh(updated_at: datetime, ttl: float) -> bool:
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)
        return datetime.now(UTC) - updated_at < timedelta(seconds=ttl)


def _encode(key: str, value: Any) -> dict[str, Any] | list[Any]:
    if key == "offers":
        return [{"id": item.id, "name": item.name} for item in value]
    return {
        "domains": _references_payload(value.domains),
        "groups": _references_payload(value.groups),
        "sources": _references_payload(value.sources),
    }


def _references_payload(items: list[Reference]) -> list[dict[str, Any]]:
    return [{"id": item.id, "name": item.name} for item in items]


def _decode(key: str, payload: dict[str, Any] | list[Any]) -> Any:
    if key == "offers":
        offers = cast(list[dict[str, Any]], payload)
        return [
            Offer(id=int(item["id"]), name=str(item["name"]))
            for item in offers
        ]
    references = cast(dict[str, list[dict[str, Any]]], payload)
    return References(
        domains=_decode_references(references["domains"]),
        groups=_decode_references(references["groups"]),
        sources=_decode_references(references["sources"]),
    )


def _decode_references(items: list[dict[str, Any]]) -> list[Reference]:
    return [Reference(id=item["id"], name=item["name"]) for item in items]
