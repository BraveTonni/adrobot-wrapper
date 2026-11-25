from app.infrastructure.keitaro.errors import KeitaroError


def test_keitaro_error_keeps_optional_status() -> None:
    error = KeitaroError("not found", status=404)

    assert str(error) == "not found"
    assert error.status == 404
    assert KeitaroError("offline").status is None
