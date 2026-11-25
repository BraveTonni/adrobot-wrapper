"""HTTP-маршруты каталога и справочников."""

from fastapi import APIRouter, Query

from app.transport.http.deps import CatalogDep
from app.transport.http.presenters.catalog import CatalogResponseFactory
from app.transport.http.schemas.catalog import (
    CatalogRefreshOut,
    OfferSummaryOut,
    ReferencesOut,
)

router = APIRouter()


@router.post("/catalog/refresh", response_model=CatalogRefreshOut)
async def refresh_catalog(catalog: CatalogDep) -> CatalogRefreshOut:
    offers, references = await catalog.refresh()
    return CatalogRefreshOut(
        offers=CatalogResponseFactory.offers(offers),
        references=CatalogResponseFactory.references(references),
    )


@router.get("/references", response_model=ReferencesOut)
async def references(catalog: CatalogDep) -> ReferencesOut:
    return CatalogResponseFactory.references(await catalog.references())


@router.get("/offers", response_model=list[OfferSummaryOut])
async def offers(
    catalog: CatalogDep,
    search: str = Query(default="", max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[OfferSummaryOut]:
    results = await catalog.search_offers(search, limit)
    return CatalogResponseFactory.offers(results)
