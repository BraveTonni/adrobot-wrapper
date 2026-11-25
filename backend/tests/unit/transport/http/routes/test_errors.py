from fastapi import FastAPI
from starlette.requests import Request

from app.application.errors import (
    ConflictError,
    ExternalServiceError,
    NotFoundError,
)
from app.transport.http.routes.errors import (
    _handle_conflict,
    _handle_external_service,
    _handle_not_found,
    register_error_handlers,
)
from app.transport.http.status import HttpStatus


def request() -> Request:
    return Request({"type": "http", "method": "GET", "path": "/"})


async def test_not_found_handler_returns_404() -> None:
    response = await _handle_not_found(request(), NotFoundError("missing"))

    assert response.status_code == HttpStatus.NOT_FOUND
    assert response.body == b'{"detail":"missing"}'


async def test_conflict_handler_returns_409() -> None:
    response = await _handle_conflict(request(), ConflictError("duplicate"))

    assert response.status_code == HttpStatus.CONFLICT
    assert response.body == b'{"detail":"duplicate"}'


async def test_external_service_handler_returns_bad_gateway() -> None:
    response = await _handle_external_service(
        request(), ExternalServiceError("offline")
    )

    assert response.status_code == HttpStatus.BAD_GATEWAY


def test_register_error_handlers_on_application() -> None:
    app = FastAPI()

    register_error_handlers(app)

    assert NotFoundError in app.exception_handlers
    assert ConflictError in app.exception_handlers
    assert ExternalServiceError in app.exception_handlers
