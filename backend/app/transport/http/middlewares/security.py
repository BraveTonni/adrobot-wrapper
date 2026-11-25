"""CORS and browser-facing security headers for the HTTP API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class SecurityHeadersMiddleware:
    """Add defensive headers to HTTP responses without buffering the body."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_security_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.setdefault("X-Content-Type-Options", "nosniff")
                headers.setdefault("X-Frame-Options", "DENY")
                headers.setdefault("Referrer-Policy", "no-referrer")
                headers.setdefault(
                    "Permissions-Policy",
                    "camera=(), microphone=(), geolocation=()",
                )
                if scope.get("path") not in {"/docs", "/redoc"}:
                    headers.setdefault(
                        "Content-Security-Policy",
                        "default-src 'none'; frame-ancestors 'none'; "
                        "base-uri 'none'",
                    )
            await send(message)

        await self.app(scope, receive, send_with_security_headers)


def install_security_middlewares(
    app: FastAPI, *, cors_allowed_origins: list[str]
) -> None:
    if "*" in cors_allowed_origins:
        raise ValueError("CORS_ALLOWED_ORIGINS must not contain '*'")
    if cors_allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_allowed_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
            max_age=600,
        )
    app.add_middleware(SecurityHeadersMiddleware)
