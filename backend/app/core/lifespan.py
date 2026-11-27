"""Инициализация и освобождение ресурсов приложения."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings, settings
from app.core.container import build_container
from app.infrastructure.logging.config import setup_logging

logger = logging.getLogger(__name__)


def validate_startup_config(config: Settings) -> None:
    """Останавливает запуск без обязательного секрета."""
    if not config.keitaro_api_key:
        raise RuntimeError(
            "KEITARO_API_KEY is not configured: set it in backend/.env "
            "or in the Pydantic secrets directory"
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    config: Settings = getattr(app.state, "settings", settings)
    setup_logging(config.log_level, config.log_directory)
    validate_startup_config(config)
    container = build_container(config)
    app.state.container = container
    logger.info(
        "application startup completed",
        extra={"editor_publish_mode": config.editor_publish_mode},
    )

    try:
        yield
    finally:
        await container.close()
        logger.info("application shutdown completed")
