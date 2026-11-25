"""Сценарии чтения кампаний и их потоков."""

from app.application.ports import CampaignReaderRepository
from app.domain.campaigns.entities import Campaign, Stream


class CampaignQueries:
    def __init__(self, repository: CampaignReaderRepository) -> None:
        self._repository = repository

    async def search(self, query: str, limit: int) -> list[Campaign]:
        if not query:
            return await self._repository.list_campaigns(limit)

        needle = query.lower()
        matches: list[Campaign] = []
        offset = 0
        while len(matches) < limit:
            page = await self._repository.list_campaigns(limit, offset)
            matches.extend(
                campaign
                for campaign in page
                if needle in campaign.name.casefold()
            )
            if len(page) < limit:
                break
            offset += len(page)
        return matches[:limit]

    async def get_with_streams(
        self, campaign_id: int
    ) -> tuple[Campaign, list[Stream]]:
        campaign = await self._repository.get_campaign(campaign_id)
        streams = await self._repository.list_streams(campaign_id)
        return campaign, streams
