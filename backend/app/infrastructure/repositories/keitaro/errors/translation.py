"""Перевод ошибок HTTP-клиента в ошибки application layer."""

from collections.abc import Awaitable

from app.application.errors import (
    ExternalServiceError,
    RepositoryNotFoundError,
)
from app.infrastructure.keitaro.errors import KeitaroError


async def execute[T](operation: Awaitable[T]) -> T:
    try:
        return await operation
    except KeitaroError as exc:
        if exc.status != 404:
            raise ExternalServiceError(str(exc), status=exc.status) from exc
        raise RepositoryNotFoundError from exc
