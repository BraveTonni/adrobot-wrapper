from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.config import Settings
from app.transport.http import security


def test_authenticated_requests_are_rate_limited(monkeypatch) -> None:
    monkeypatch.setattr(
        security,
        "_request_rate_limiter",
        security._WindowRateLimiter(attempts=1),
    )
    request = SimpleNamespace(client=SimpleNamespace(host="198.51.100.42"))
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="a" * 32
    )
    config = Settings(_env_file=None, api_access_token="a" * 32)

    security.require_api_access(request, credentials, config)

    with pytest.raises(HTTPException) as error:
        security.require_api_access(request, credentials, config)

    assert error.value.status_code == 429
    assert error.value.headers == {"Retry-After": "60"}
