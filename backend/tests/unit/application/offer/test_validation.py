from unittest.mock import AsyncMock

import pytest

from app.application.errors import NotFoundError, RepositoryNotFoundError
from app.application.offer.validation import ensure_offer_exists


@pytest.mark.asyncio
async def test_existing_offer_passes_validation() -> None:
    client = AsyncMock()

    await ensure_offer_exists(client, 5)

    client.get_offer.assert_awaited_once_with(5)


@pytest.mark.asyncio
async def test_missing_offer_becomes_not_found_error() -> None:
    client = AsyncMock()
    client.get_offer.side_effect = RepositoryNotFoundError

    with pytest.raises(NotFoundError, match="#5"):
        await ensure_offer_exists(client, 5)


@pytest.mark.asyncio
async def test_other_repository_errors_are_preserved() -> None:
    client = AsyncMock()
    error = RuntimeError("offline")
    client.get_offer.side_effect = error

    with pytest.raises(RuntimeError) as raised:
        await ensure_offer_exists(client, 5)

    assert raised.value is error
