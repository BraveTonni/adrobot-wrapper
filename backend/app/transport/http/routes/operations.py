"""HTTP-маршрут истории операций."""

from fastapi import APIRouter

from app.transport.http.deps import OperationHistoryDep
from app.transport.http.presenters.operations import OperationResponseFactory
from app.transport.http.schemas.operations import OperationOut

router = APIRouter()


@router.get("/operations", response_model=list[OperationOut])
async def operations(history: OperationHistoryDep) -> list[OperationOut]:
    return OperationResponseFactory.operations(await history.recent())
