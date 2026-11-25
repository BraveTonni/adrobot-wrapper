"""Authentication dependencies for protected HTTP routes."""

import hmac
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings
from app.transport.http.deps import get_settings

_bearer = HTTPBearer(auto_error=False)


def require_api_access(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer)
    ],
    config: Annotated[Settings, Depends(get_settings)],
) -> None:
    if not config.api_access_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API access token is not configured",
        )
    if credentials is None or not hmac.compare_digest(
        credentials.credentials.encode(), config.api_access_token.encode()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
