"""SQL persistence for campaign creation snapshots."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.application.errors import RepositoryNotFoundError
from app.domain.campaigns.entities import Campaign, Stream, StreamOffer
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

    async def sync(self, campaign: Campaign, streams: list[Stream]) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                snapshot = await session.get(CampaignSnapshot, campaign.id)
                if snapshot is None:
                    snapshot = CampaignSnapshot(
                        id=campaign.id,
                        name=campaign.name,
                    )
                    session.add(snapshot)
                snapshot.name = campaign.name
                snapshot.alias = campaign.alias
                snapshot.type = campaign.type
                snapshot.state = campaign.state
                snapshot.domain_id = campaign.domain_id
                snapshot.group_id = campaign.group_id
                snapshot.traffic_source_id = campaign.traffic_source_id
                await session.flush()

                remote_stream_ids = {stream.id for stream in streams}
                existing_streams = await session.scalars(
                    select(StreamSnapshot).where(
                        StreamSnapshot.campaign_id == campaign.id
                    )
                )
                for existing_stream in existing_streams:
                    if existing_stream.id not in remote_stream_ids:
                        await session.delete(existing_stream)

                for stream in streams:
                    await self._sync_stream_in_session(session, stream)

    async def get_stream(self, campaign_id: int, stream_id: int) -> Stream:
        async with self._session_factory() as session:
            result = await session.scalars(
                select(StreamSnapshot)
                .options(selectinload(StreamSnapshot.offers))
                .where(
                    StreamSnapshot.id == stream_id,
                    StreamSnapshot.campaign_id == campaign_id,
                )
            )
            snapshot = result.one_or_none()
            if snapshot is None:
                raise RepositoryNotFoundError
            return _stream_from_snapshot(snapshot)

    async def list_streams(self, campaign_id: int) -> list[Stream]:
        async with self._session_factory() as session:
            snapshots = await session.scalars(
                select(StreamSnapshot)
                .options(selectinload(StreamSnapshot.offers))
                .where(StreamSnapshot.campaign_id == campaign_id)
                .order_by(StreamSnapshot.position, StreamSnapshot.id)
            )
            return [_stream_from_snapshot(item) for item in snapshots]

    async def save_offers(
        self, stream_id: int, offers: list[StreamOffer]
    ) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                stream = await session.get(StreamSnapshot, stream_id)
                if stream is None:
                    raise RepositoryNotFoundError
                rows = await session.scalars(
                    select(StreamOfferSnapshot).where(
                        StreamOfferSnapshot.stream_id == stream_id
                    )
                )
                stored = {row.offer_id: row for row in rows}
                incoming_ids = {offer.offer_id for offer in offers}
                for offer in offers:
                    row = stored.get(offer.offer_id)
                    if row is None:
                        row = StreamOfferSnapshot(
                            stream_id=stream_id,
                            offer_id=offer.offer_id,
                            share=offer.share,
                            state=offer.state,
                            published_share=offer.published_share or 0,
                            published_state=offer.published_state,
                            draft_share=offer.draft_share or 0,
                            draft_state=offer.draft_state,
                            is_pinned=offer.is_pinned,
                            is_deleted=offer.is_deleted,
                            metadata_payload=offer.metadata,
                        )
                        session.add(row)
                    else:
                        _copy_offer_to_snapshot(offer, row)
                for offer_id, row in stored.items():
                    if offer_id not in incoming_ids:
                        await session.delete(row)

    async def sync_stream(self, stream: Stream) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                await self._sync_stream_in_session(
                    session, stream, after_push=True
                )

    async def _sync_stream_in_session(
        self,
        session: AsyncSession,
        remote: Stream,
        *,
        after_push: bool = False,
    ) -> None:
        snapshot = await session.get(StreamSnapshot, remote.id)
        if snapshot is None:
            snapshot = StreamSnapshot(
                id=remote.id,
                campaign_id=remote.campaign_id,
                name=remote.name,
                type=remote.type,
                schema=remote.schema,
                position=remote.position,
                state=remote.state,
                raw_payload=remote.raw_payload,
            )
            session.add(snapshot)
            await session.flush()
        else:
            snapshot.name = remote.name
            snapshot.type = remote.type
            snapshot.schema = remote.schema
            snapshot.position = remote.position
            snapshot.state = remote.state
            snapshot.raw_payload = remote.raw_payload

        rows = await session.scalars(
            select(StreamOfferSnapshot).where(
                StreamOfferSnapshot.stream_id == remote.id
            )
        )
        stored = {row.offer_id: row for row in rows}
        remote_ids = {offer.offer_id for offer in remote.offers}
        for offer in remote.offers:
            row = stored.get(offer.offer_id)
            if row is None:
                row = StreamOfferSnapshot(
                    stream_id=remote.id,
                    offer_id=offer.offer_id,
                    share=offer.share,
                    state=offer.state,
                    published_share=offer.share,
                    published_state=offer.state,
                    draft_share=offer.share,
                    draft_state=offer.state,
                    is_pinned=offer.is_pinned,
                    is_deleted=False,
                    metadata_payload=offer.metadata,
                )
                session.add(row)
                continue

            is_dirty = _snapshot_has_draft(row)
            row.published_share = offer.share
            row.published_state = offer.state
            row.metadata_payload = offer.metadata
            if not is_dirty:
                row.draft_share = offer.share
                row.draft_state = offer.state
                row.is_pinned = offer.is_pinned
                row.is_deleted = False
            row.share = row.draft_share
            row.state = row.draft_state

        for offer_id, row in stored.items():
            if offer_id in remote_ids:
                continue
            if (
                after_push
                and row.published_state == "deleted"
                and row.published_share == 0
            ):
                await session.delete(row)
                continue
            is_dirty = _snapshot_has_draft(row)
            row.published_state = "deleted"
            if not is_dirty:
                row.draft_state = "deleted"
                row.is_deleted = True
            row.state = row.draft_state
            row.share = row.draft_share


def _snapshot_has_draft(snapshot: StreamOfferSnapshot) -> bool:
    deleted_in_both_states = (
        snapshot.is_deleted
        and snapshot.draft_state == "deleted"
        and snapshot.published_state == "deleted"
    )
    return (
        snapshot.draft_state != snapshot.published_state
        or (
            not deleted_in_both_states
            and snapshot.draft_share != snapshot.published_share
        )
        or snapshot.is_deleted != (snapshot.published_state == "deleted")
    )


def _copy_offer_to_snapshot(
    offer: StreamOffer, snapshot: StreamOfferSnapshot
) -> None:
    snapshot.share = offer.share
    snapshot.state = offer.state
    snapshot.is_pinned = offer.is_pinned
    snapshot.published_share = offer.published_share or 0
    snapshot.published_state = offer.published_state
    snapshot.draft_share = offer.draft_share or 0
    snapshot.draft_state = offer.draft_state
    snapshot.is_deleted = offer.is_deleted
    snapshot.metadata_payload = offer.metadata


def _stream_from_snapshot(snapshot: StreamSnapshot) -> Stream:
    offers = [
        StreamOffer(
            offer_id=offer.offer_id,
            share=offer.draft_share,
            state=offer.draft_state,
            metadata=offer.metadata_payload,
            is_pinned=offer.is_pinned,
            published_share=offer.published_share,
            published_state=offer.published_state,
            draft_share=offer.draft_share,
            draft_state=offer.draft_state,
            is_deleted=offer.is_deleted,
        )
        for offer in snapshot.offers
    ]
    return Stream(
        id=snapshot.id,
        campaign_id=snapshot.campaign_id,
        name=snapshot.name,
        type=snapshot.type,
        schema=snapshot.schema,
        position=snapshot.position,
        state=snapshot.state,
        offers=offers,
        raw_payload=snapshot.raw_payload,
    )
