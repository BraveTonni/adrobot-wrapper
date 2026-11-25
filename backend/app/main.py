"""Сборка и запуск приложения."""

from fastapi import FastAPI

from app.core.lifespan import lifespan
from app.transport.http.routes import router
from app.transport.http.routes.errors import register_error_handlers


def create_app() -> FastAPI:
    app = FastAPI(title="adrobot-wrapper", lifespan=lifespan)
    register_error_handlers(app)
    app.include_router(router)
    return app


app = create_app()
