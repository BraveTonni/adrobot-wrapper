"""Схемы HTTP API: запросы, ответы и сборка ответов из DTO Keitaro."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.countries import is_country_code
from app.keitaro.schemas import Campaign, Stream


class CampaignCreate(BaseModel):
    """POST /api/campaigns."""

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


class OfferAdd(BaseModel):
    """POST /api/campaigns/{id}/streams/{sid}/offers."""

    offer_id: int = Field(gt=0)


class OfferOut(BaseModel):
    offer_id: int
    name: str | None = None
    share: int
    state: str | None = None


class StreamOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str | None
    type: str | None
    schema_: str | None = Field(default=None, alias="schema")
    uses_offers: bool
    offers: list[OfferOut]


class CampaignOut(BaseModel):
    id: int
    name: str
    alias: str | None
    admin_url: str
    streams: list[StreamOut]


def admin_url(campaign_id: int, admin_base_url: str) -> str:
    base = admin_base_url.rstrip("/")

    return f"{base}/#!/campaign.editor/{campaign_id}"


def stream_out(stream: Stream, names: dict[int, str]) -> StreamOut:
    return StreamOut(
        id=stream.id,
        name=stream.name,
        type=stream.type,
        schema=stream.schema_,
        uses_offers=stream.uses_offers,
        offers=[
            OfferOut(
                offer_id=offer.offer_id,
                name=names.get(offer.offer_id),
                share=offer.share,
                state=offer.state,
            )
            for offer in stream.offers
        ],
    )


def campaign_out(
    campaign: Campaign,
    streams: list[Stream],
    names: dict[int, str],
    admin_base_url: str,
) -> CampaignOut:
    return CampaignOut(
        id=campaign.id,
        name=campaign.name,
        alias=campaign.alias,
        admin_url=admin_url(campaign.id, admin_base_url),
        streams=[stream_out(stream, names) for stream in streams],
    )
