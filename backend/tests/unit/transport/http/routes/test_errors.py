import json

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request

from app.application.errors import (
    ConflictError,
    ExternalServiceError,
    NotFoundError,
    RepositoryNotFoundError,
)
from app.transport.http.errors import ApiError
from app.transport.http.routes.errors import (
    _handle_api_error,
    _handle_conflict,
    _handle_external_service,
    _handle_invalid_request,
    _handle_not_found,
    _handle_repository_not_found,
    _handle_unexpected,
    register_error_handlers,
)
from app.transport.http.status import HttpStatus


def request() -> Request:
    return Request({"type": "http", "method": "GET", "path": "/"})


def body(response: object) -> dict[str, object]:
    return json.loads(response.body)  # type: ignore[attr-defined]


async def test_not_found_handler_returns_404() -> None:
    response = await _handle_not_found(request(), NotFoundError("missing"))

    assert response.status_code == HttpStatus.NOT_FOUND
    assert body(response) == {"detail": "missing"}


async def test_repository_not_found_handler_returns_404_with_text() -> None:
    response = await _handle_repository_not_found(
        request(), RepositoryNotFoundError()
    )

    assert response.status_code == HttpStatus.NOT_FOUND
    assert body(response) == {"detail": "Запрошенный объект не найден"}


async def test_conflict_handler_returns_409() -> None:
    response = await _handle_conflict(request(), ConflictError("duplicate"))

    assert response.status_code == HttpStatus.CONFLICT
    assert body(response) == {"detail": "duplicate"}


async def test_external_service_handler_returns_bad_gateway() -> None:
    response = await _handle_external_service(
        request(), ExternalServiceError("offline")
    )

    assert response.status_code == HttpStatus.BAD_GATEWAY


async def test_api_error_handler_adds_machine_readable_code() -> None:
    response = await _handle_api_error(
        request(), ApiError(409, "pending", code="idempotency_pending")
    )

    assert response.status_code == HttpStatus.CONFLICT
    assert body(response) == {
        "detail": "pending",
        "code": "idempotency_pending",
    }


async def test_invalid_request_handler_flattens_schema_errors() -> None:
    error = RequestValidationError(
        [
            {
                "loc": ("body", "geo"),
                "msg": "Value error, не является кодом ISO",
                "type": "value_error",
                "input": "XX",
            },
            {
                "loc": ("body", "offer_id"),
                "msg": "Input should be greater than 0",
                "type": "greater_than",
                "input": 0,
            },
        ]
    )

    response = await _handle_invalid_request(request(), error)

    assert response.status_code == HttpStatus.UNPROCESSABLE_ENTITY
    assert body(response) == {
        "detail": (
            "geo: Value error, не является кодом ISO; "
            "offer_id: Input should be greater than 0"
        )
    }


async def test_unexpected_error_handler_hides_internal_details() -> None:
    response = await _handle_unexpected(
        request(), RuntimeError("password=hunter2 at /etc/passwd")
    )

    assert response.status_code == HttpStatus.INTERNAL_SERVER_ERROR
    assert body(response) == {"detail": "Внутренняя ошибка сервера"}


def test_register_error_handlers_on_application() -> None:
    app = FastAPI()

    register_error_handlers(app)

    assert ApiError in app.exception_handlers
    assert NotFoundError in app.exception_handlers
    assert RepositoryNotFoundError in app.exception_handlers
    assert ConflictError in app.exception_handlers
    assert ExternalServiceError in app.exception_handlers
    assert RequestValidationError in app.exception_handlers
    assert Exception in app.exception_handlers
