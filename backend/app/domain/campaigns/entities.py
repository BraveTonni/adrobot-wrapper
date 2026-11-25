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
    is_pinned: bool = False
    published_state: str | None = None
    published_share: int | None = None
    draft_state: str | None = None
    draft_share: int | None = None
    is_deleted: bool = False

    def __post_init__(self) -> None:
        published_state = (
            self.state
            if self.published_state is None
            else self.published_state
        )
        published_share = (
            self.share
            if self.published_share is None
            else self.published_share
        )
        draft_state = (
            self.state if self.draft_state is None else self.draft_state
        )
        draft_share = (
            self.share if self.draft_share is None else self.draft_share
        )
        object.__setattr__(self, "published_state", published_state)
        object.__setattr__(self, "published_share", published_share)
        object.__setattr__(self, "draft_state", draft_state)
        object.__setattr__(self, "draft_share", draft_share)
        object.__setattr__(self, "state", draft_state)
        object.__setattr__(self, "share", draft_share)


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
    raw_payload: dict[str, Any] = field(default_factory=dict)

    @property
    def uses_offers(self) -> bool:
        return self.schema == "landings"
