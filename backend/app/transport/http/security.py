"""Authentication dependencies for protected HTTP routes."""

import hmac
import time
from collections import OrderedDict, deque
from math import ceil
from threading import Lock
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings
from app.transport.http.deps import get_settings

_bearer = HTTPBearer(auto_error=False)


class _FailedAuthLimiter:
    """Bounded per-process window for failed bearer-token attempts."""

    def __init__(self, attempts: int = 8, window_seconds: int = 60) -> None:
        self._attempt_limit = attempts
        self._window_seconds = window_seconds
        self._failures: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = Lock()

    def record_failure(self, client_key: str) -> int | None:
        now = time.monotonic()
        cutoff = now - self._window_seconds
        with self._lock:
            failures = self._failures.get(client_key)
            if failures is None:
                if len(self._failures) >= 4096:
                    self._failures.popitem(last=False)
                failures = deque()
                self._failures[client_key] = failures
            else:
                self._failures.move_to_end(client_key)
            while failures and failures[0] <= cutoff:
                failures.popleft()
            if len(failures) >= self._attempt_limit:
                return max(1, ceil(failures[0] + self._window_seconds - now))
            failures.append(now)
            return None

    def clear(self, client_key: str) -> None:
        with self._lock:
            self._failures.pop(client_key, None)


_failed_auth_limiter = _FailedAuthLimiter()


def require_api_access(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer)
    ],
    config: Annotated[Settings, Depends(get_settings)],
) -> None:
    client_key = request.client.host if request.client else "unknown"
    if len(config.api_access_token) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API access token is not configured",
        )
    if credentials is None or not hmac.compare_digest(
        credentials.credentials.encode(), config.api_access_token.encode()
    ):
        retry_after = _failed_auth_limiter.record_failure(client_key)
        if retry_after is not None:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed authentication attempts",
                headers={"Retry-After": str(retry_after)},
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    _failed_auth_limiter.clear(client_key)
