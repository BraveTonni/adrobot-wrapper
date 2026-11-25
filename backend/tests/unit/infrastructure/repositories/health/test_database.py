from unittest.mock import AsyncMock, MagicMock

import pytest

from app.infrastructure.repositories.health.database import SqlHealthRepository


@pytest.mark.asyncio
async def test_health_repository_executes_database_probe() -> None:
    session = AsyncMock()
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=session)
    context.__aexit__ = AsyncMock(return_value=None)
    factory = MagicMock(return_value=context)

    await SqlHealthRepository(factory).check_database()

    session.execute.assert_awaited_once()
