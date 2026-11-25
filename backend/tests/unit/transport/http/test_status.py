from app.transport.http.status import HttpStatus


def test_http_status_values() -> None:
    assert HttpStatus.CREATED == 201
    assert HttpStatus.NOT_FOUND == 404
    assert HttpStatus.CONFLICT == 409
    assert HttpStatus.BAD_GATEWAY == 502
