import pytest

from app.config import Settings
from app.infrastructure.keitaro.client import KeitaroClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_list_offers_returns_list_from_keitaro() -> None:
    settings = Settings()
    if not settings.keitaro_api_key:
        pytest.skip(
            "KEITARO_API_KEY is required for Keitaro integration tests"
        )

    client = KeitaroClient(settings)
    try:
        offers = await client.list_offers()
    finally:
        await client.aclose()

    assert isinstance(offers, list)
