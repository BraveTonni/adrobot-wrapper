from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.transport.http.routes.health import health


@pytest.mark.asyncio
async def test_health_returns_application_status() -> None:
    check = SimpleNamespace(check=AsyncMock(return_value={"status": "ok"}))

    result = await health(check)

    assert result == {"status": "ok"}
    check.check.assert_awaited_once()
