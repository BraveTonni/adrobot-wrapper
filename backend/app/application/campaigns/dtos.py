"""Команды сценариев управления кампаниями."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreateCampaign:
    name: str
    domain_id: int
    group_id: int
    traffic_source_id: int


@dataclass(frozen=True, slots=True)
class CampaignDefaults:
    domain_id: int
    group_id: int
    traffic_source_id: int
