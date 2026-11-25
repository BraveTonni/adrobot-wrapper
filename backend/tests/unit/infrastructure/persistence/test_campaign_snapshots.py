import pytest
from sqlalchemy import select

from app.domain.campaigns.entities import Campaign, Stream, StreamOffer
from app.domain.campaigns.offer_state import has_draft
from app.infrastructure.persistence.campaigns import (
    SqlCampaignSnapshotRepository,
)
from app.infrastructure.persistence.database import (
    build_engine,
    build_session_factory,
)
from app.infrastructure.persistence.models import Base
from app.infrastructure.persistence.models.campaign_snapshot import (
    CampaignSnapshot,
    StreamOfferSnapshot,
    StreamSnapshot,
)


@pytest.mark.asyncio
async def test_saves_campaign_stream_and_offer_snapshots() -> None:
    engine = build_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = build_session_factory(engine)
    repository = SqlCampaignSnapshotRepository(factory)

    await repository.save(
        Campaign(id=7, name="Campaign", alias="campaign"),
        [
            Stream(
                id=11,
                campaign_id=7,
                name="Offers",
                schema="landings",
                raw_payload={"schema": "landings", "filters": []},
                offers=[
                    StreamOffer(
                        offer_id=5,
                        share=75,
                        state="active",
                        is_pinned=True,
                        published_share=100,
                        draft_share=75,
                        metadata={"custom": "value"},
                    )
                ],
            )
        ],
    )

    async with factory() as session:
        campaign = await session.get(CampaignSnapshot, 7)
        stream = await session.get(StreamSnapshot, 11)
        offer = await session.get(StreamOfferSnapshot, (11, 5))

    assert campaign is not None and campaign.name == "Campaign"
    assert stream is not None
    assert stream.raw_payload == {"schema": "landings", "filters": []}
    assert offer is not None and offer.share == 75
    assert offer.published_share == 100
    assert offer.draft_share == 75
    assert offer.is_pinned
    assert offer.metadata_payload == {"custom": "value"}
    await engine.dispose()


@pytest.mark.asyncio
async def test_replacing_snapshot_cascades_old_streams_and_offers() -> None:
    engine = build_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = build_session_factory(engine)
    repository = SqlCampaignSnapshotRepository(factory)
    campaign = Campaign(id=7, name="Campaign")

    await repository.save(
        campaign,
        [Stream(id=11, campaign_id=7, offers=[StreamOffer(offer_id=5)])],
    )
    await repository.save(
        campaign,
        [Stream(id=12, campaign_id=7, offers=[StreamOffer(offer_id=6)])],
    )

    async with factory() as session:
        stream_ids = list(await session.scalars(select(StreamSnapshot.id)))
        offer_ids = list(
            await session.scalars(select(StreamOfferSnapshot.offer_id))
        )

    assert stream_ids == [12]
    assert offer_ids == [6]
    await engine.dispose()


@pytest.mark.asyncio
async def test_sync_preserves_drafts_until_push() -> None:
    engine = build_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = build_session_factory(engine)
    repository = SqlCampaignSnapshotRepository(factory)
    campaign = Campaign(id=7, name="Campaign")
    await repository.save(
        campaign,
        [
            Stream(
                id=11,
                campaign_id=7,
                name="Offers",
                schema="landings",
                offers=[
                    StreamOffer(offer_id=5, share=50, state="active"),
                    StreamOffer(offer_id=6, share=50, state="active"),
                ],
            )
        ],
    )

    await repository.save_offers(
        11,
        [
            StreamOffer(
                offer_id=5,
                share=100,
                state="active",
                published_share=50,
                published_state="active",
                draft_share=100,
                draft_state="active",
            ),
            StreamOffer(
                offer_id=6,
                share=40,
                state="deleted",
                published_share=50,
                published_state="active",
                draft_share=40,
                draft_state="deleted",
                is_deleted=True,
            ),
        ],
    )

    await repository.sync(
        campaign,
        [
            Stream(
                id=11,
                campaign_id=7,
                name="Offers",
                schema="landings",
                offers=[
                    StreamOffer(offer_id=5, share=50, state="active"),
                    StreamOffer(offer_id=6, share=50, state="active"),
                ],
            )
        ],
    )
    draft = await repository.get_stream(7, 11)
    assert [offer.share for offer in draft.offers] == [100, 40]
    assert [offer.published_share for offer in draft.offers] == [50, 50]
    assert draft.offers[1].is_deleted
    assert all(has_draft(offer) for offer in draft.offers)

    await repository.sync_stream(
        Stream(
            id=11,
            campaign_id=7,
            name="Offers",
            schema="landings",
            offers=[StreamOffer(offer_id=5, share=100, state="active")],
        )
    )
    published = await repository.get_stream(7, 11)
    assert [offer.offer_id for offer in published.offers] == [5, 6]
    assert published.offers[0].published_share == 100
    assert published.offers[1].published_state == "deleted"
    assert not any(has_draft(offer) for offer in published.offers)
    await engine.dispose()


@pytest.mark.asyncio
async def test_sync_keeps_new_draft_offer_and_push_reconciles_it() -> None:
    engine = build_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = build_session_factory(engine)
    repository = SqlCampaignSnapshotRepository(factory)
    campaign = Campaign(id=7, name="Campaign")
    await repository.save(
        campaign,
        [
            Stream(
                id=11,
                campaign_id=7,
                name="Offers",
                schema="landings",
                offers=[StreamOffer(offer_id=5, share=100, state="active")],
            )
        ],
    )
    await repository.save_offers(
        11,
        [
            StreamOffer(
                offer_id=5,
                share=50,
                state="active",
                published_share=100,
                published_state="active",
                draft_share=50,
            ),
            StreamOffer(
                offer_id=6,
                share=50,
                state="active",
                published_share=0,
                published_state="deleted",
                draft_share=50,
                draft_state="active",
            ),
        ],
    )

    await repository.sync(
        campaign,
        [
            Stream(
                id=11,
                campaign_id=7,
                name="Offers",
                schema="landings",
                offers=[StreamOffer(offer_id=5, share=100, state="active")],
            )
        ],
    )
    draft = await repository.get_stream(7, 11)
    assert [offer.offer_id for offer in draft.offers] == [5, 6]
    assert draft.offers[1].published_share == 0

    await repository.sync_stream(
        Stream(
            id=11,
            campaign_id=7,
            name="Offers",
            schema="landings",
            offers=[
                StreamOffer(offer_id=5, share=50, state="active"),
                StreamOffer(offer_id=6, share=50, state="active"),
            ],
        )
    )
    published = await repository.get_stream(7, 11)
    assert [offer.offer_id for offer in published.offers] == [5, 6]
    assert published.offers[1].published_share == 50
    assert not any(has_draft(offer) for offer in published.offers)
    await engine.dispose()
