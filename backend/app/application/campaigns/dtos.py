"""Команды сценариев управления кампаниями."""

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class CreateCampaign:
    name: str
    alias: str
    domain_id: int
    group_id: int
    traffic_source_id: int


@dataclass(frozen=True, slots=True)
class CreateStream:
    campaign_id: int
    name: str
    type: Literal["regular", "forced", "default"]
    schema: Literal["redirect", "landings", "action"]
    position: int
    action_type: str
    action_payload: str | None = None
    filters: tuple[dict[str, Any], ...] = ()
    offers: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True, slots=True)
class CampaignStreamDefinition:
    name: str
    type: Literal["regular", "forced", "default"]
    schema: Literal["redirect", "landings", "action"]
    position: int
    action_type: str = "http"
    action_payload: str | None = None
    filters: tuple[dict[str, Any], ...] = ()
    initial_offer: bool = False


@dataclass(frozen=True, slots=True)
class CampaignDefaults:
    domain_id: int
    group_id: int
    traffic_source_id: int
