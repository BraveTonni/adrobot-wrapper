"""Тела запросов Admin API."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class StreamFilter(BaseModel):
    """Фильтр страны в теле POST /streams."""

    name: str
    mode: str
    payload: Any = None


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
