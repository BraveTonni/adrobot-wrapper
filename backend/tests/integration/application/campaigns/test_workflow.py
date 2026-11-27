import os
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.application.campaigns.creator import CampaignCreator
from app.application.campaigns.dtos import CampaignDefaults
from app.application.campaigns.editor import CampaignEditor
from app.application.campaigns.streams import CampaignStreamsCreator
from app.config import Settings
from app.infrastructure.keitaro.client import KeitaroClient
from app.infrastructure.repositories.keitaro.campaigns import (
    KeitaroCampaignRepository,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_campaign_create_and_offer_edit_round_trip() -> None:
    settings = Settings()
    if not settings.keitaro_api_key:
        pytest.skip(
            "KEITARO_API_KEY is required for Keitaro integration tests"
        )

    campaign_prefix = os.getenv("KEITARO_TEST_CAMPAIGN_PREFIX")
    if not campaign_prefix:
        pytest.skip("KEITARO_TEST_CAMPAIGN_PREFIX is required")
    if not campaign_prefix.startswith("test_"):
        pytest.fail("KEITARO_TEST_CAMPAIGN_PREFIX must start with 'test_'")

    client = KeitaroClient(settings)
    repository = KeitaroCampaignRepository(client)
    campaign_id: int | None = None

    try:
        offers = await client.list_offers()
        if len(offers) < 2:
            pytest.skip("The test requires at least two Keitaro offers")

        audit = AsyncMock()
        defaults = CampaignDefaults(
            domain_id=settings.default_domain_id,
            group_id=settings.default_group_id,
            traffic_source_id=settings.default_source_id,
        )
        creator = CampaignCreator(
            repository,
            audit,
            CampaignStreamsCreator(repository),
            defaults,
        )
        editor = CampaignEditor(repository, audit)

        campaign, streams = await creator.create(
            name=f"{campaign_prefix}backend_smoke_{uuid4().hex[:8]}",
            alias=f"test-backend-smoke-{uuid4().hex[:8]}",
            geo="US",
            offer_id=offers[0].id,
        )
        campaign_id = campaign.id
        saved_campaign = await repository.get_campaign(campaign.id)

        assert len(streams) == 2
        assert saved_campaign.type == "position"
        assert saved_campaign.domain_id == settings.default_domain_id
        assert saved_campaign.group_id == settings.default_group_id
        assert saved_campaign.traffic_source_id == settings.default_source_id
        geo_stream, offer_stream = streams
        assert geo_stream.position == 1
        assert geo_stream.schema == "redirect"
        assert offer_stream.position == 2
        assert offer_stream.uses_offers
        assert [
            (offer.offer_id, offer.share) for offer in offer_stream.offers
        ] == [(offers[0].id, 100)]

        updated_stream = await editor.add_offer(
            campaign.id, offer_stream.id, offers[1].id
        )

        assert [offer.share for offer in updated_stream.offers] == [50, 50]

        restored_stream = await editor.remove_offer(
            campaign.id, offer_stream.id, offers[1].id
        )

        assert [offer.share for offer in restored_stream.offers] == [100]
        assert [offer.offer_id for offer in restored_stream.offers] == [
            offers[0].id
        ]
    finally:
        try:
            if campaign_id is not None:
                await repository.delete_campaign(campaign_id)
        finally:
            await client.aclose()
