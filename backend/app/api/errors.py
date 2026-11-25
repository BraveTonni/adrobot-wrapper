"""Маппинг ошибок приложения на HTTP-ответы."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.keitaro.errors import KeitaroError
from app.services.errors import Conflict, NotFound


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(NotFound, _handle_not_found)
    app.add_exception_handler(Conflict, _handle_conflict)
    app.add_exception_handler(KeitaroError, _handle_keitaro)


async def _handle_not_found(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=404)


async def _handle_conflict(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=409)


async def _handle_keitaro(request: Request, exc: Exception) -> JSONResponse:
    status = 502
    if isinstance(exc, KeitaroError) and exc.status == 404:
        status = 404

    return JSONResponse({"detail": str(exc)}, status_code=status)
