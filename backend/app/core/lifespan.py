"""Инициализация и освобождение ресурсов приложения."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings, settings
from app.core.container import build_container
from app.infrastructure.logging.config import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    config: Settings = getattr(app.state, "settings", settings)
    setup_logging(config.log_level)
    container = build_container(config)
    app.state.container = container

    try:
        yield
    finally:
        await container.close()
