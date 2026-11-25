"""TTL-кэширующая обёртка над репозиторием каталога."""

from app.application.catalog.dtos import References
from app.application.ports import CatalogRepository
from app.domain.catalog.entities import Offer
from app.infrastructure.cache.ttl import TTLCache


class CachedCatalogRepository:
    def __init__(
        self,
        repository: CatalogRepository,
        *,
        offers_ttl: float,
        references_ttl: float,
    ) -> None:
        self._repository = repository
        self._offers: TTLCache[list[Offer]] = TTLCache(offers_ttl)
        self._references: TTLCache[References] = TTLCache(references_ttl)

    async def list_offers(self) -> list[Offer]:
        return await self._offers.get(self._repository.list_offers)

    async def list_references(self) -> References:
        return await self._references.get(self._repository.list_references)
