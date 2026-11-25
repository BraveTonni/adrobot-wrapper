"""Сценарии чтения кампаний и их потоков."""

from app.application.ports import CampaignReaderRepository
from app.domain.campaigns.entities import Campaign, Stream


class CampaignQueries:
    def __init__(self, repository: CampaignReaderRepository) -> None:
        self._repository = repository

    async def search(self, query: str, limit: int) -> list[Campaign]:
        campaigns = await self._repository.list_campaigns(limit)
        if not query:
            return campaigns

        needle = query.lower()
        return [
            campaign
            for campaign in campaigns
            if needle in campaign.name.lower()
        ]

    async def get_with_streams(
        self, campaign_id: int
    ) -> tuple[Campaign, list[Stream]]:
        campaign = await self._repository.get_campaign(campaign_id)
        streams = await self._repository.list_streams(campaign_id)
        return campaign, streams
