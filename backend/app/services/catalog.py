"""Справочники Keitaro с кэшем в памяти процесса."""

import asyncio
from dataclasses import dataclass

from app.config import Settings, settings
from app.keitaro.client import KeitaroClient
from app.keitaro.schemas import CampaignGroup, Domain, Offer, TrafficSource
from app.services.cache import TtlCache


@dataclass
class References:
    domains: list[Domain]
    groups: list[CampaignGroup]
    sources: list[TrafficSource]


class Catalog:
    def __init__(
        self, client: KeitaroClient, config: Settings = settings
    ) -> None:
        self._client = client
        self._offers: TtlCache[list[Offer]] = TtlCache(config.offers_cache_ttl)
        self._refs: TtlCache[References] = TtlCache(config.reference_cache_ttl)

    async def offers(self) -> list[Offer]:
        return await self._offers.get(self._client.list_offers)

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
        return await self._refs.get(self._load_references)

    async def _load_references(self) -> References:
        domains, groups, sources = await asyncio.gather(
            self._client.list_domains(),
            self._client.list_groups(),
            self._client.list_sources(),
        )
        return References(domains=domains, groups=groups, sources=sources)
