"""Преобразование ошибок приложения в ответы HTTP API."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.application.errors import (
    ConflictError,
    ExternalServiceError,
    NotFoundError,
)
from app.transport.http.status import HttpStatus


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(NotFoundError, _handle_not_found)
    app.add_exception_handler(ConflictError, _handle_conflict)
    app.add_exception_handler(ExternalServiceError, _handle_external_service)


async def _handle_not_found(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=HttpStatus.NOT_FOUND)


async def _handle_conflict(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=HttpStatus.CONFLICT)


async def _handle_external_service(
    request: Request, exc: Exception
) -> JSONResponse:
    return JSONResponse(
        {"detail": str(exc)}, status_code=HttpStatus.BAD_GATEWAY
    )
