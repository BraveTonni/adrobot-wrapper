from starlette.requests import Request

from app.transport.http.audit import audit_actor


def make_request(
    headers: list[tuple[bytes, bytes]],
    client: tuple[str, int] | None = ("127.0.0.1", 1234),
) -> Request:
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/v1/campaigns",
            "raw_path": b"/api/v1/campaigns",
            "query_string": b"",
            "headers": headers,
            "client": client,
            "server": ("testserver", 80),
        }
    )


def test_audit_actor_normalizes_user_header() -> None:
    request = make_request([(b"x-user", b"  qa   user  ")])

    assert audit_actor(request) == "qa user"


def test_audit_actor_falls_back_to_client_ip_then_unknown() -> None:
    assert audit_actor(make_request([])) == "127.0.0.1"
    assert audit_actor(make_request([], client=None)) == "unknown"
