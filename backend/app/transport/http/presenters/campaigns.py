"""Представление кампаний и потоков в HTTP API."""

from app.domain.campaigns.entities import Campaign, Stream
from app.domain.catalog.entities import Offer
from app.transport.http.schemas.campaigns import (
    CampaignOut,
    CampaignSummaryOut,
)
from app.transport.http.schemas.streams import OfferOut, StreamOut


class CampaignResponseFactory:
    @staticmethod
    def campaign(
        campaign: Campaign,
        streams: list[Stream],
        offers: list[Offer],
        admin_base_url: str,
    ) -> CampaignOut:
        base = admin_base_url.rstrip("/")
        return CampaignOut(
            id=campaign.id,
            name=campaign.name,
            alias=campaign.alias,
            admin_url=f"{base}/#!/campaign.editor/{campaign.id}",
            streams=[
                CampaignResponseFactory.stream(stream, offers)
                for stream in streams
            ],
        )

    @staticmethod
    def stream(stream: Stream, offers: list[Offer]) -> StreamOut:
        names = {offer.id: offer.name for offer in offers}
        return StreamOut(
            id=stream.id,
            name=stream.name,
            type=stream.type,
            schema=stream.schema,
            uses_offers=stream.uses_offers,
            offers=[
                OfferOut(
                    offer_id=offer.offer_id,
                    name=names.get(offer.offer_id),
                    share=offer.share,
                    state=offer.state,
                )
                for offer in stream.offers
            ],
        )

    @staticmethod
    def campaigns(campaigns: list[Campaign]) -> list[CampaignSummaryOut]:
        return [
            CampaignSummaryOut(
                id=campaign.id,
                name=campaign.name,
                alias=campaign.alias,
            )
            for campaign in campaigns
        ]
