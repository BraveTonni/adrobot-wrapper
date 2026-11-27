from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI

import app.core.lifespan as lifecycle
from app.config import Settings


def app_with(config: Settings) -> FastAPI:
    app = FastAPI()
    app.state.settings = config
    return app


@pytest.mark.asyncio
async def test_lifespan_builds_container_and_closes_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    container = SimpleNamespace(close=AsyncMock())
    monkeypatch.setattr(
        lifecycle, "setup_logging", lambda level, directory: None
    )
    monkeypatch.setattr(lifecycle, "build_container", lambda config: container)
    app = app_with(Settings(_env_file=None, keitaro_api_key="test-key"))

    async with lifecycle.lifespan(app):
        assert app.state.container is container

    container.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifespan_refuses_to_start_without_keitaro_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    container = SimpleNamespace(close=AsyncMock())
    monkeypatch.delenv("KEITARO_API_KEY", raising=False)
    monkeypatch.setattr(
        lifecycle, "setup_logging", lambda level, directory: None
    )
    monkeypatch.setattr(lifecycle, "build_container", lambda config: container)
    app = app_with(Settings(_env_file=None))

    with pytest.raises(RuntimeError, match="KEITARO_API_KEY"):
        async with lifecycle.lifespan(app):
            pytest.fail("приложение не должно стартовать без ключа")

    container.close.assert_not_awaited()
