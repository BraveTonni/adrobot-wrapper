"""CORS and browser-facing security headers for the HTTP API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_MAX_REQUEST_BODY_BYTES = 64 * 1024


class _RequestBodyTooLarge(Exception):
    pass


class RequestBodyLimitMiddleware:
    """Reject oversized HTTP request bodies before route processing."""

    def __init__(
        self, app: ASGIApp, max_body_bytes: int = _MAX_REQUEST_BODY_BYTES
    ) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if scope["type"] != "http" or scope["method"] in {
            "GET",
            "HEAD",
            "OPTIONS",
        }:
            await self.app(scope, receive, send)
            return

        content_length = Headers(scope=scope).get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.max_body_bytes:
                    await self._reject(send)
                    return
            except ValueError:
                await self._reject(send)
                return

        received_bytes = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received_bytes
            message = await receive()
            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > self.max_body_bytes:
                    raise _RequestBodyTooLarge
            return message

        async def track_response(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, track_response)
        except _RequestBodyTooLarge:
            if not response_started:
                await self._reject(send)

    @staticmethod
    async def _reject(send: Send) -> None:
        body = b'{"detail":"Request body exceeds the 64 KiB limit"}'
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send(
            {"type": "http.response.body", "body": body, "more_body": False}
        )


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
    app.add_middleware(RequestBodyLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
