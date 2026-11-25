"""HTTP-маршруты, сгруппированные по ресурсам API."""

from fastapi import APIRouter

from app.transport.http.routes.campaigns import router as campaigns_router
from app.transport.http.routes.catalog import router as catalog_router
from app.transport.http.routes.health import router as health_router
from app.transport.http.routes.operations import router as operations_router

router = APIRouter(prefix="/api")
router.include_router(health_router)
router.include_router(catalog_router)
router.include_router(campaigns_router)
router.include_router(operations_router)
