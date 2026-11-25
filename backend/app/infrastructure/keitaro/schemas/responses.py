"""Модели ответов Admin API.

Описываются только используемые поля, остальные игнорируются,
чтобы новые поля Keitaro не ломали сервис.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.infrastructure.keitaro.schemas.base import KeitaroModel


class Offer(KeitaroModel):
    id: int
    name: str


class Domain(KeitaroModel):
    id: int
    name: str


class CampaignGroup(KeitaroModel):
    id: int
    name: str


class TrafficSource(KeitaroModel):
    id: int
    name: str


class Campaign(KeitaroModel):
    id: int
    name: str
    alias: str | None = None
    type: str | None = None
    state: str | None = None
    domain_id: int | None = None
    group_id: int | None = None
    traffic_source_id: int | None = None


class StreamOffer(BaseModel):
    """Форма оффера в ответах Keitaro Admin API."""

    model_config = ConfigDict(extra="allow")

    offer_id: int
    share: int = 0
    state: str | None = None


class Stream(KeitaroModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: int
    campaign_id: int
    name: str | None = None
    type: str | None = None
    schema_: str | None = Field(default=None, alias="schema")
    position: int | None = None
    state: str | None = None
    offers: list[StreamOffer] = Field(default_factory=list)
