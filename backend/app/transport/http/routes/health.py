"""HTTP-маршрут состояния сервиса."""

from fastapi import APIRouter

from app.transport.http.deps import HealthCheckDep

router = APIRouter()


@router.get("/health")
async def health(check: HealthCheckDep) -> dict[str, str]:
    return await check.check()
