"""Инициализация и освобождение ресурсов приложения."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings, settings
from app.core.container import build_container
from app.infrastructure.logging.config import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    config: Settings = getattr(app.state, "settings", settings)
    setup_logging(config.log_level, config.log_directory)
    container = build_container(config)
    app.state.container = container
    logger.info("application startup completed")

    try:
        yield
    finally:
        await container.close()
        logger.info("application shutdown completed")
