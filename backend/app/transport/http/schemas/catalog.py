"""HTTP-контракты каталога и справочников."""

from pydantic import BaseModel


class OfferSummaryOut(BaseModel):
    id: int
    name: str


class ReferenceOut(BaseModel):
    id: int
    name: str


class ReferencesOut(BaseModel):
    domains: list[ReferenceOut]
    groups: list[ReferenceOut]
    sources: list[ReferenceOut]


class CatalogRefreshOut(BaseModel):
    offers: list[OfferSummaryOut]
    references: ReferencesOut
