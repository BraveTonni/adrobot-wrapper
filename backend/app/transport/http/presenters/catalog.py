"""Представление каталога и справочников в HTTP API."""

from app.application.catalog.dtos import References
from app.domain.catalog.entities import Offer, Reference
from app.transport.http.schemas.catalog import (
    OfferSummaryOut,
    ReferenceOut,
    ReferencesOut,
)


class CatalogResponseFactory:
    @staticmethod
    def offers(offers: list[Offer]) -> list[OfferSummaryOut]:
        return [
            OfferSummaryOut(id=offer.id, name=offer.name) for offer in offers
        ]

    @staticmethod
    def references(references: References) -> ReferencesOut:
        def map_items(items: list[Reference]) -> list[ReferenceOut]:
            return [ReferenceOut(id=item.id, name=item.name) for item in items]

        return ReferencesOut(
            domains=map_items(references.domains),
            groups=map_items(references.groups),
            sources=map_items(references.sources),
        )
