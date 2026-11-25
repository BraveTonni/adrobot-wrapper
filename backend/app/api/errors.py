"""Маппинг ошибок приложения на HTTP-ответы."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.status import HttpStatus
from app.keitaro.errors import KeitaroError
from app.services.errors import ConflictError, NotFoundError


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(NotFoundError, _handle_not_found)
    app.add_exception_handler(ConflictError, _handle_conflict)
    app.add_exception_handler(KeitaroError, _handle_keitaro)


async def _handle_not_found(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=HttpStatus.NOT_FOUND)


async def _handle_conflict(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=HttpStatus.CONFLICT)


async def _handle_keitaro(request: Request, exc: Exception) -> JSONResponse:
    status = HttpStatus.BAD_GATEWAY
    if isinstance(exc, KeitaroError) and exc.status == HttpStatus.NOT_FOUND:
        status = HttpStatus.NOT_FOUND

    return JSONResponse({"detail": str(exc)}, status_code=status)
