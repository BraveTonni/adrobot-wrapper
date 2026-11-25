"""Сборка и запуск приложения."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from starlette.middleware.base import RequestResponseEndpoint

from app.config import Settings, settings
from app.core.lifespan import lifespan
from app.transport.http.routes import router
from app.transport.http.routes.errors import register_error_handlers


def create_app(config: Settings | None = None) -> FastAPI:
    config = config or settings
    app = FastAPI(title="adrobot-wrapper", lifespan=lifespan)
    app.state.settings = config
    if "*" in config.cors_allowed_origins:
        raise ValueError("CORS_ALLOWED_ORIGINS must not contain '*'")
    if config.cors_allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_allowed_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
            max_age=600,
        )

    @app.middleware("http")
    async def add_security_headers(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        if request.url.path not in {"/docs", "/redoc"}:
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
            )
        return response

    register_error_handlers(app)
    app.include_router(router)
    return app


app = create_app()
