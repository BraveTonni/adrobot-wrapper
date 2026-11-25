"""Сущности кампаний и потоков."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Campaign:
    id: int
    name: str
    alias: str | None = None
    type: str | None = None
    state: str | None = None
    domain_id: int | None = None
    group_id: int | None = None
    traffic_source_id: int | None = None


@dataclass(frozen=True, slots=True)
class StreamOffer:
    offer_id: int
    share: int = 0
    state: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Stream:
    id: int
    campaign_id: int
    name: str | None = None
    type: str | None = None
    schema: str | None = None
    position: int | None = None
    state: str | None = None
    offers: list[StreamOffer] = field(default_factory=list)

    @property
    def uses_offers(self) -> bool:
        return self.schema == "landings"
