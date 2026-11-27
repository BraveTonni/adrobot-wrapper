"""Keitaro-репозиторий кампаний и потоков."""

from app.application.campaigns.dtos import CreateCampaign, CreateStream
from app.domain.campaigns.entities import Campaign, Stream, StreamOffer
from app.domain.catalog.entities import Offer
from app.infrastructure.keitaro.client import KeitaroClient
from app.infrastructure.keitaro.mappers.campaigns import (
    campaign_create_to_keitaro,
    campaign_to_domain,
)
from app.infrastructure.keitaro.mappers.catalog import offer_to_domain
from app.infrastructure.keitaro.mappers.streams import (
    stream_offer_to_keitaro,
    stream_to_domain,
)
from app.infrastructure.keitaro.schemas import StreamCreate, StreamFilter
from app.infrastructure.repositories.keitaro.errors.translation import execute

READ_ONLY_STREAM_FIELDS = frozenset({"id", "created_at", "updated_at"})


class KeitaroCampaignRepository:
    def __init__(self, client: KeitaroClient) -> None:
        self._client = client

    async def get_offer(self, offer_id: int) -> Offer:
        offer = await execute(self._client.get_offer(offer_id))
        return offer_to_domain(offer)

    async def create_campaign(self, command: CreateCampaign) -> Campaign:
        request = campaign_create_to_keitaro(command)
        campaign = await execute(self._client.create_campaign(request))
        return campaign_to_domain(campaign)

    async def delete_campaign(self, campaign_id: int) -> None:
        await execute(self._client.delete_campaign(campaign_id))

    async def create_stream(self, command: CreateStream) -> Stream:
        request = StreamCreate(
            campaign_id=command.campaign_id,
            name=command.name,
            type=command.type,
            schema=command.schema,
            position=command.position,
            action_type=command.action_type,
            action_payload=command.action_payload,
            filters=[
                StreamFilter.model_validate(item) for item in command.filters
            ]
            or None,
            offers=list(command.offers) or None,
        )
        stream = await execute(self._client.create_stream(request))
        return stream_to_domain(stream)

    async def list_campaigns(
        self, limit: int, offset: int = 0
    ) -> list[Campaign]:
        campaigns = await execute(self._client.list_campaigns(limit, offset))
        return [campaign_to_domain(campaign) for campaign in campaigns]

    async def get_campaign(self, campaign_id: int) -> Campaign:
        campaign = await execute(self._client.get_campaign(campaign_id))
        return campaign_to_domain(campaign)

    async def list_streams(self, campaign_id: int) -> list[Stream]:
        streams = await execute(self._client.list_streams(campaign_id))
        return [stream_to_domain(stream) for stream in streams]

    async def get_stream(self, stream_id: int) -> Stream:
        stream = await execute(self._client.get_stream(stream_id))
        return stream_to_domain(stream)

    async def update_stream(
        self,
        stream_id: int,
        offers: list[StreamOffer],
        *,
        current: Stream | None = None,
    ) -> Stream:
        """Заменяет офферы потока, сохраняя его остальные настройки.

        `current` — уже прочитанный поток; без него настройки перечитываются.
        """
        if current is None:
            current = await self.get_stream(stream_id)
        payload = {
            key: value
            for key, value in current.raw_payload.items()
            if key not in READ_ONLY_STREAM_FIELDS
        }
        payload["offers"] = [
            stream_offer_to_keitaro(offer) for offer in offers
        ]
        stream = await execute(self._client.update_stream(stream_id, payload))
        return stream_to_domain(stream)
