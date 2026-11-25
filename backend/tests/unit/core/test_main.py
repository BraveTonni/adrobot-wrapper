import app.main as main
from app.application.errors import (
    ConflictError,
    ExternalServiceError,
    NotFoundError,
)


def test_create_app_registers_api_routes() -> None:
    app = main.create_app()

    paths = set(app.openapi()["paths"])
    assert "/api/v1/campaigns" in paths
    assert "/api/v1/operations" in paths
    assert "/api/campaigns" not in paths


def test_create_app_registers_application_error_handlers() -> None:
    app = main.create_app()

    assert NotFoundError in app.exception_handlers
    assert ConflictError in app.exception_handlers
    assert ExternalServiceError in app.exception_handlers
