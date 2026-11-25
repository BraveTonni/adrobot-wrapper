"""HTTP-маршрут истории операций."""

from fastapi import APIRouter, HTTPException

from app.transport.http.deps import OperationHistoryDep
from app.transport.http.idempotency_deps import IdempotencyDep
from app.transport.http.presenters.operations import OperationResponseFactory
from app.transport.http.schemas.operations import OperationOut

router = APIRouter()


@router.get("/operations", response_model=list[OperationOut])
async def operations(history: OperationHistoryDep) -> list[OperationOut]:
    return OperationResponseFactory.operations(await history.recent())


@router.delete("/operations/idempotency/{key}")
async def release_stale_idempotency_key(
    key: str, idempotency: IdempotencyDep
) -> dict[str, str]:
    released = await idempotency.release_stale(key)
    if not released:
        raise HTTPException(
            status_code=409,
            detail="Key is missing or has no stale pending reservation",
        )
    return {"detail": "Stale reservation released after manual reconciliation"}
