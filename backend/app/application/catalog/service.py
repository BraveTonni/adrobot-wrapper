"""Прикладные сценарии чтения каталога офферов и справочников."""

from app.application.catalog.dtos import References
from app.application.ports import CatalogRepository
from app.domain.catalog.entities import Offer


class Catalog:
    def __init__(self, repository: CatalogRepository) -> None:
        self._repository = repository

    async def offers(self) -> list[Offer]:
        return await self._repository.list_offers()

    async def search_offers(self, query: str, limit: int) -> list[Offer]:
        items = await self.offers()
        if query:
            needle = query.lower()
            items = [
                item
                for item in items
                if needle in item.name.lower() or needle in str(item.id)
            ]
        return items[:limit]

    async def references(self) -> References:
        return await self._repository.list_references()

    async def refresh(self) -> tuple[list[Offer], References]:
        await self._repository.refresh()
        return await self.offers(), await self.references()
