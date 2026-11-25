"""Keitaro-репозиторий кампаний и потоков."""

from app.application.campaigns.dtos import CreateCampaign
from app.domain.campaigns.entities import Campaign, Stream, StreamOffer
from app.domain.catalog.entities import Offer
from app.infrastructure.keitaro.client import KeitaroClient
from app.infrastructure.keitaro.mappers.campaigns import (
    campaign_create_to_keitaro,
    campaign_to_domain,
)
from app.infrastructure.keitaro.mappers.catalog import offer_to_domain
from app.infrastructure.keitaro.mappers.streams import (
    geo_stream_to_keitaro,
    offer_stream_to_keitaro,
    stream_offer_to_keitaro,
    stream_to_domain,
)
from app.infrastructure.repositories.keitaro.errors.translation import execute


class KeitaroCampaignRepository:
    def __init__(self, client: KeitaroClient, geo_redirect_url: str) -> None:
        self._client = client
        self._geo_redirect_url = geo_redirect_url

    async def get_offer(self, offer_id: int) -> Offer:
        offer = await execute(self._client.get_offer(offer_id))
        return offer_to_domain(offer)

    async def create_campaign(self, command: CreateCampaign) -> Campaign:
        request = campaign_create_to_keitaro(command)
        campaign = await execute(self._client.create_campaign(request))
        return campaign_to_domain(campaign)

    async def delete_campaign(self, campaign_id: int) -> None:
        await execute(self._client.delete_campaign(campaign_id))

    async def create_geo_stream(self, campaign_id: int, geo: str) -> Stream:
        request = geo_stream_to_keitaro(
            campaign_id, geo, self._geo_redirect_url
        )
        stream = await execute(self._client.create_stream(request))
        return stream_to_domain(stream)

    async def create_offer_stream(
        self, campaign_id: int, offer_id: int
    ) -> Stream:
        request = offer_stream_to_keitaro(campaign_id, offer_id)
        stream = await execute(self._client.create_stream(request))
        return stream_to_domain(stream)

    async def list_campaigns(
        self, limit: int, offset: int = 0
    ) -> list[Campaign]:
        campaigns = await execute(
            self._client.list_campaigns(limit, offset)
        )
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
        self, stream_id: int, offers: list[StreamOffer]
    ) -> Stream:
        payload = {
            "offers": [stream_offer_to_keitaro(offer) for offer in offers]
        }
        stream = await execute(self._client.update_stream(stream_id, payload))
        return stream_to_domain(stream)
