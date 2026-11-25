from unittest.mock import AsyncMock

import pytest

from app.application.health.check import HealthCheck


@pytest.mark.asyncio
async def test_health_check_returns_ok_after_repository_check() -> None:
    repository = AsyncMock()

    result = await HealthCheck(repository).check()

    assert result == {"status": "ok"}
    repository.check_database.assert_awaited_once()
