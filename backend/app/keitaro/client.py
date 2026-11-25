"""Тонкий HTTP-клиент Admin API: только запросы и ошибка при не-2xx."""

from typing import Any

import httpx

from app.config import settings
from app.keitaro.errors import KeitaroError
from app.keitaro.schemas import (
    Campaign,
    CampaignCreate,
    CampaignGroup,
    Domain,
    Offer,
    Stream,
    StreamCreate,
    TrafficSource,
)


class KeitaroClient:
    def __init__(self) -> None:
        self._http = httpx.AsyncClient(
            base_url=settings.keitaro_url,
            timeout=settings.keitaro_timeout,
            headers={"Api-Key": settings.keitaro_api_key},
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = await self._http.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise KeitaroError(f"Keitaro недоступен: {exc}") from exc
        if response.status_code >= 400:
            raise KeitaroError(
                f"{method} {path} -> HTTP {response.status_code}: "
                f"{response.text[:300]}",
                status=response.status_code,
            )
        if not response.content:
            return None
        return response.json()

    # --- кампании -------------------------------------------------------

    async def list_campaigns(self, limit: int) -> list[Campaign]:
        data = await self._request(
            "GET", "/campaigns", params={"offset": 0, "limit": limit}
        )
        return [Campaign.model_validate(item) for item in _list(data)]

    async def get_campaign(self, campaign_id: int) -> Campaign:
        data = await self._request("GET", f"/campaigns/{campaign_id}")
        return Campaign.model_validate(_one(data, "кампанию"))

    async def create_campaign(self, payload: CampaignCreate) -> Campaign:
        data = await self._request("POST", "/campaigns", json=payload.to_api())
        return Campaign.model_validate(_one(data, "кампанию"))

    async def delete_campaign(self, campaign_id: int) -> None:
        await self._request("DELETE", f"/campaigns/{campaign_id}")

    # --- потоки ---------------------------------------------------------

    async def list_streams(self, campaign_id: int) -> list[Stream]:
        data = await self._request("GET", f"/campaigns/{campaign_id}/streams")
        return [Stream.model_validate(item) for item in _list(data)]

    async def get_stream(self, stream_id: int) -> Stream:
        data = await self._request("GET", f"/streams/{stream_id}")
        return Stream.model_validate(_one(data, "поток"))

    async def create_stream(self, payload: StreamCreate) -> Stream:
        data = await self._request("POST", "/streams", json=payload.to_api())
        return Stream.model_validate(_one(data, "поток"))

    async def update_stream(
        self, stream_id: int, payload: dict[str, Any]
    ) -> Stream:
        data = await self._request(
            "PUT", f"/streams/{stream_id}", json=payload
        )
        return Stream.model_validate(_one(data, "поток"))

    # --- справочники ----------------------------------------------------

    async def list_offers(self) -> list[Offer]:
        data = await self._request("GET", "/offers")
        return [Offer.model_validate(item) for item in _list(data)]

    async def get_offer(self, offer_id: int) -> Offer:
        data = await self._request("GET", f"/offers/{offer_id}")
        return Offer.model_validate(_one(data, "оффер"))

    async def list_domains(self) -> list[Domain]:
        data = await self._request("GET", "/domains")
        return [Domain.model_validate(item) for item in _list(data)]

    async def list_groups(self) -> list[CampaignGroup]:
        data = await self._request(
            "GET", "/groups", params={"type": "campaigns"}
        )
        return [CampaignGroup.model_validate(item) for item in _list(data)]

    async def list_sources(self) -> list[TrafficSource]:
        data = await self._request("GET", "/traffic_sources")
        return [TrafficSource.model_validate(item) for item in _list(data)]


def _list(data: Any) -> list[dict[str, Any]]:
    """Список объектов; допускает обёртку в dict с data/items/results."""
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("data", "items", "results"):
            if isinstance(data.get(key), list):
                return [item for item in data[key] if isinstance(item, dict)]
    return []


def _one(data: Any, entity: str) -> dict[str, Any]:
    """Один объект; API может отвечать списком из одного элемента."""
    if isinstance(data, list) and data:
        data = data[0]
    if not isinstance(data, dict) or data.get("id") is None:
        raise KeitaroError(f"Keitaro не вернул ID {entity}")
    return data
