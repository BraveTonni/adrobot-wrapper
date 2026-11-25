import pytest
from starlette.types import Message, Receive, Scope, Send

from app.transport.http.middlewares import RequestBodyLimitMiddleware


@pytest.mark.asyncio
async def test_body_limit_rejects_large_declared_content_length() -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        pytest.fail("oversized request must be rejected before the app")

    async def receive() -> Message:
        pytest.fail("oversized request body must not be read")

    sent: list[Message] = []

    async def send(message: Message) -> None:
        sent.append(message)

    middleware = RequestBodyLimitMiddleware(app, max_body_bytes=4)
    await middleware(
        {
            "type": "http",
            "method": "POST",
            "path": "/",
            "headers": [(b"content-length", b"5")],
            "asgi": {"version": "3.0"},
        },
        receive,
        send,
    )

    assert sent[0]["status"] == 413


@pytest.mark.asyncio
async def test_body_limit_also_catches_chunked_request_bodies() -> None:
    app_called = False
    messages = iter(
        [
            {"type": "http.request", "body": b"1234", "more_body": True},
            {"type": "http.request", "body": b"5", "more_body": False},
        ]
    )

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        nonlocal app_called
        app_called = True
        await receive()
        await receive()

    async def receive() -> Message:
        return next(messages)

    sent: list[Message] = []

    async def send(message: Message) -> None:
        sent.append(message)

    await RequestBodyLimitMiddleware(app, max_body_bytes=4)(
        {
            "type": "http",
            "method": "POST",
            "path": "/",
            "headers": [],
            "asgi": {"version": "3.0"},
        },
        receive,
        send,
    )

    assert app_called
    assert sent[0]["status"] == 413
