from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI

import app.core.lifespan as lifecycle


@pytest.mark.asyncio
async def test_lifespan_builds_container_and_closes_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    container = SimpleNamespace(close=AsyncMock())
    monkeypatch.setattr(lifecycle, "setup_logging", lambda level: None)
    monkeypatch.setattr(lifecycle, "build_container", lambda config: container)
    app = FastAPI()

    async with lifecycle.lifespan(app):
        assert app.state.container is container

    container.close.assert_awaited_once()
