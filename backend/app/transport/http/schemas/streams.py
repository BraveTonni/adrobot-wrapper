"""HTTP-контракты потоков кампании."""

from pydantic import BaseModel, ConfigDict, Field


class OfferAdd(BaseModel):
    """POST /api/v1/campaigns/{id}/streams/{sid}/offers."""

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
