"""Keitaro-репозиторий каталога офферов и справочников."""

import asyncio

from app.application.catalog.dtos import References
from app.domain.catalog.entities import Offer
from app.infrastructure.keitaro.client import KeitaroClient
from app.infrastructure.keitaro.mappers.catalog import (
    offer_to_domain,
    reference_to_domain,
)
from app.infrastructure.repositories.keitaro.errors.translation import execute


class KeitaroCatalogRepository:
    def __init__(self, client: KeitaroClient) -> None:
        self._client = client

    async def list_offers(self) -> list[Offer]:
        offers = await execute(self._client.list_offers())
        return [offer_to_domain(offer) for offer in offers]

    async def list_references(self) -> References:
        domains, groups, sources = await asyncio.gather(
            execute(self._client.list_domains()),
            execute(self._client.list_groups()),
            execute(self._client.list_sources()),
        )
        return References(
            domains=[reference_to_domain(item) for item in domains],
            groups=[reference_to_domain(item) for item in groups],
            sources=[reference_to_domain(item) for item in sources],
        )
