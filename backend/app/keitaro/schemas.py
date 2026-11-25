"""Pydantic-модели ответов Admin API.

Описываются только используемые поля, остальные игнорируются,
чтобы новые поля Keitaro не ломали сервис.
"""

from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field


class KeitaroModel(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


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


class StreamFilter(KeitaroModel):
    name: str
    mode: str
    payload: Any = None


class StreamOffer(BaseModel):
    """Оффер в потоке.

    Неизвестные поля сохраняются: PUT /streams/{id} заменяет
    весь offers, поэтому ответ Keitaro нужно вернуть обратно
    (кроме служебных полей) с пересчитанной долей.
    """

    model_config = ConfigDict(extra="allow")

    offer_id: int
    share: int = 0
    state: str | None = None

    READ_ONLY_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {"id", "stream_id", "created_at", "updated_at"}
    )

    def to_api(self, share: int) -> dict[str, Any]:
        data = self.model_dump(exclude_none=True)
        for key in self.READ_ONLY_FIELDS:
            data.pop(key, None)
        data["share"] = share
        return data


class Stream(KeitaroModel):
    id: int
    campaign_id: int
    name: str | None = None
    type: str | None = None
    schema_: str | None = Field(default=None, alias="schema")
    position: int | None = None
    state: str | None = None
    offers: list[StreamOffer] = Field(default_factory=list)

    @property
    def uses_offers(self) -> bool:
        return self.schema_ == "landings"


class CampaignCreate(BaseModel):
    """Тело POST /campaigns."""

    name: str
    type: Literal["position", "weight"] = "position"
    domain_id: int
    group_id: int
    traffic_source_id: int

    def to_api(self) -> dict[str, Any]:
        return self.model_dump()


class StreamCreate(BaseModel):
    """Тело POST /streams."""

    campaign_id: int
    name: str
    type: Literal["regular", "forced", "default"]
    schema_: Literal["redirect", "landings", "action"] = Field(alias="schema")
    position: int | None = None
    action_type: str | None = None
    action_payload: str | None = None
    filters: list[StreamFilter] | None = None
    offers: list[dict[str, Any]] | None = None

    def to_api(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_none=True)
