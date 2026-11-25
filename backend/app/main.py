"""Сборка и запуск приложения."""

from fastapi import FastAPI

from app.config import Settings, settings
from app.core.lifespan import lifespan
from app.transport.http.routes import router
from app.transport.http.routes.errors import register_error_handlers


def create_app(config: Settings | None = None) -> FastAPI:
    app = FastAPI(title="adrobot-wrapper", lifespan=lifespan)
    app.state.settings = config or settings
    register_error_handlers(app)
    app.include_router(router)
    return app


app = create_app()
