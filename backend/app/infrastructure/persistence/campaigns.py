"""SQL persistence for campaign creation snapshots."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.campaigns.entities import Campaign, Stream
from app.infrastructure.persistence.models.campaign_snapshot import (
    CampaignSnapshot,
    StreamOfferSnapshot,
    StreamSnapshot,
)


class SqlCampaignSnapshotRepository:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        self._session_factory = session_factory

    async def save(self, campaign: Campaign, streams: list[Stream]) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                existing = await session.get(CampaignSnapshot, campaign.id)
                if existing is not None:
                    await session.delete(existing)
                    await session.flush()

                snapshot = CampaignSnapshot(
                    id=campaign.id,
                    name=campaign.name,
                    alias=campaign.alias,
                    type=campaign.type,
                    state=campaign.state,
                    domain_id=campaign.domain_id,
                    group_id=campaign.group_id,
                    traffic_source_id=campaign.traffic_source_id,
                    streams=[
                        StreamSnapshot(
                            id=stream.id,
                            campaign_id=campaign.id,
                            name=stream.name,
                            type=stream.type,
                            schema=stream.schema,
                            position=stream.position,
                            state=stream.state,
                            raw_payload=stream.raw_payload,
                            offers=[
                                StreamOfferSnapshot(
                                    offer_id=offer.offer_id,
                                    share=offer.share,
                                    state=offer.state,
                                    is_pinned=offer.is_pinned,
                                    published_share=offer.published_share,
                                    published_state=offer.published_state,
                                    draft_share=offer.draft_share,
                                    draft_state=offer.draft_state,
                                    is_deleted=offer.is_deleted,
                                    metadata_payload=offer.metadata,
                                )
                                for offer in stream.offers
                            ],
                        )
                        for stream in streams
                    ],
                )
                session.add(snapshot)
