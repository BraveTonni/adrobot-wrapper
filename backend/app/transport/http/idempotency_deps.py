"""Resolution of idempotency storage for HTTP routes."""

from typing import Annotated, cast

from fastapi import Depends, Request

from app.application.idempotency import IdempotencyRepository


def get_idempotency(request: Request) -> IdempotencyRepository:
    return cast(IdempotencyRepository, request.app.state.container.idempotency)


IdempotencyDep = Annotated[
    IdempotencyRepository, Depends(get_idempotency)
]
