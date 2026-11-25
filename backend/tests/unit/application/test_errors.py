from app.application.errors import ConflictError, NotFoundError


def test_service_errors_keep_messages() -> None:
    assert str(NotFoundError("missing")) == "missing"
    assert str(ConflictError("duplicate")) == "duplicate"
