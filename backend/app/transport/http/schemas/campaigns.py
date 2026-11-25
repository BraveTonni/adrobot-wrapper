"""HTTP-контракты кампаний."""

from pydantic import BaseModel, Field, field_validator

from app.domain.countries import is_country_code
from app.transport.http.schemas.streams import StreamOut


class CampaignCreate(BaseModel):
    """POST /api/v1/campaigns."""

    name: str = Field(min_length=1, max_length=255)
    geo: str
    offer_id: int = Field(gt=0)
    domain_id: int | None = Field(default=None, gt=0)
    group_id: int | None = Field(default=None, gt=0)
    source_id: int | None = Field(default=None, gt=0)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("название не может быть пустым")
        return value

    @field_validator("geo")
    @classmethod
    def _validate_geo(cls, value: str) -> str:
        code = value.strip().upper()
        if not is_country_code(code):
            raise ValueError(f"{value!r} не является кодом ISO 3166-1 alpha-2")

        return code


class CampaignOut(BaseModel):
    id: int
    name: str
    alias: str | None
    admin_url: str
    streams: list[StreamOut]


class CampaignSummaryOut(BaseModel):
    id: int
    name: str
    alias: str | None
