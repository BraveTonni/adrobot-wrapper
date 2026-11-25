"""Сборка и запуск приложения."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.routes import router
from app.config import settings
from app.keitaro.client import KeitaroClient
from app.logging_config import setup_logging
from app.services.catalog import Catalog
from app.storage.db import build_engine, build_session_factory


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging(settings.log_level)
    engine = build_engine()
    app.state.engine = engine
    app.state.session_factory = build_session_factory(engine)
    app.state.client = KeitaroClient()
    app.state.catalog = Catalog(app.state.client)
    yield
    await app.state.client.aclose()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="adrobot-wrapper", lifespan=lifespan)
    register_error_handlers(app)
    app.include_router(router)
    return app


app = create_app()
