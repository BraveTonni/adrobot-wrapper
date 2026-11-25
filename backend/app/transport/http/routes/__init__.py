"""HTTP-маршруты, сгруппированные по ресурсам API."""

from fastapi import APIRouter, Depends

from app.constants.api import API_PREFIX
from app.transport.http.routes.campaigns import router as campaigns_router
from app.transport.http.routes.catalog import router as catalog_router
from app.transport.http.routes.health import router as health_router
from app.transport.http.routes.operations import router as operations_router
from app.transport.http.security import require_api_access

router = APIRouter(prefix=API_PREFIX)
router.include_router(health_router)
router.include_router(catalog_router)
router.include_router(
    campaigns_router, dependencies=[Depends(require_api_access)]
)
router.include_router(
    operations_router, dependencies=[Depends(require_api_access)]
)
