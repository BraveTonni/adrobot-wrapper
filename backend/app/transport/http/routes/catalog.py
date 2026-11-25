"""HTTP-маршруты каталога и справочников."""

from fastapi import APIRouter, Query

from app.transport.http.deps import CatalogDep
from app.transport.http.presenters.catalog import CatalogResponseFactory
from app.transport.http.schemas.catalog import OfferSummaryOut, ReferencesOut

router = APIRouter()


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
