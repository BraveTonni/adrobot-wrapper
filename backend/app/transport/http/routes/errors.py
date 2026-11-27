"""Преобразование ошибок приложения в ответы HTTP API."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.application.errors import (
    ConflictError,
    ExternalServiceError,
    NotFoundError,
    RepositoryNotFoundError,
    ValidationError,
)
from app.transport.http.errors import ApiError
from app.transport.http.status import HttpStatus

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, _handle_api_error)
    app.add_exception_handler(NotFoundError, _handle_not_found)
    app.add_exception_handler(
        RepositoryNotFoundError, _handle_repository_not_found
    )
    app.add_exception_handler(ConflictError, _handle_conflict)
    app.add_exception_handler(ExternalServiceError, _handle_external_service)
    app.add_exception_handler(ValidationError, _handle_validation)
    app.add_exception_handler(RequestValidationError, _handle_invalid_request)
    app.add_exception_handler(Exception, _handle_unexpected)


async def _handle_api_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ApiError)
    body: dict[str, object] = {"detail": exc.detail}
    if exc.code is not None:
        body["code"] = exc.code
    return JSONResponse(body, status_code=exc.status_code)


async def _handle_not_found(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=HttpStatus.NOT_FOUND)


async def _handle_repository_not_found(
    request: Request, exc: Exception
) -> JSONResponse:
    detail = str(exc) or "Запрошенный объект не найден"
    return JSONResponse({"detail": detail}, status_code=HttpStatus.NOT_FOUND)


async def _handle_conflict(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=HttpStatus.CONFLICT)


async def _handle_external_service(
    request: Request, exc: Exception
) -> JSONResponse:
    return JSONResponse(
        {"detail": str(exc)}, status_code=HttpStatus.BAD_GATEWAY
    )


async def _handle_validation(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        {"detail": str(exc)}, status_code=HttpStatus.UNPROCESSABLE_ENTITY
    )


async def _handle_invalid_request(
    request: Request, exc: Exception
) -> JSONResponse:
    """Сводит ошибки схемы к строке: все ответы имеют вид {"detail": "..."}."""
    assert isinstance(exc, RequestValidationError)
    summary = "; ".join(_describe(error) for error in exc.errors())
    return JSONResponse(
        {"detail": summary or "Запрос не прошёл валидацию"},
        status_code=HttpStatus.UNPROCESSABLE_ENTITY,
    )


async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
    """Не отдаёт внутренние детали и трассировку клиенту."""
    logger.error(
        "необработанная ошибка при обработке запроса",
        extra={
            "method": request.method,
            "path": request.scope.get("path", "-"),
        },
        exc_info=exc,
    )
    return JSONResponse(
        {"detail": "Внутренняя ошибка сервера"},
        status_code=HttpStatus.INTERNAL_SERVER_ERROR,
    )


def _describe(error: dict[str, Any]) -> str:
    # loc начинается с места в запросе (body); он не для пользователя.
    location = ".".join(str(part) for part in error.get("loc", ())[1:])
    message = str(error.get("msg", "некорректное значение"))
    return f"{location}: {message}" if location else message
