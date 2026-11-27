from unittest.mock import AsyncMock

import pytest

from app.application.errors import (
    ExternalServiceError,
    RepositoryNotFoundError,
)
from app.infrastructure.keitaro.errors import KeitaroError
from app.infrastructure.repositories.keitaro.errors.translation import execute


@pytest.mark.asyncio
async def test_execute_maps_http_404_to_repository_not_found() -> None:
    operation = AsyncMock(side_effect=KeitaroError("missing", status=404))

    with pytest.raises(RepositoryNotFoundError):
        await execute(operation())


@pytest.mark.asyncio
async def test_execute_maps_service_errors_to_external_error() -> None:
    operation = AsyncMock(side_effect=KeitaroError("offline", status=503))

    with pytest.raises(ExternalServiceError, match="offline"):
        await execute(operation())


@pytest.mark.asyncio
async def test_execute_keeps_the_upstream_status() -> None:
    operation = AsyncMock(side_effect=KeitaroError("rejected", status=400))

    with pytest.raises(ExternalServiceError) as caught:
        await execute(operation())

    assert caught.value.status == 400
    assert isinstance(caught.value.__cause__, KeitaroError)


@pytest.mark.asyncio
async def test_execute_reports_transport_failures_without_a_status() -> None:
    operation = AsyncMock(side_effect=KeitaroError("Keitaro недоступен"))

    with pytest.raises(ExternalServiceError) as caught:
        await execute(operation())

    assert caught.value.status is None
