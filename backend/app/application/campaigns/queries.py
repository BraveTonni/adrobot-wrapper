"""Сценарии чтения кампаний и их потоков."""

from app.application.errors import NotFoundError, RepositoryNotFoundError
from app.application.ports import (
    CampaignReaderRepository,
    CampaignSnapshotRepository,
)
from app.domain.campaigns.entities import Campaign, Stream

# Keitaro может ограничивать размер страницы, поэтому поиск читает страницы
# фиксированного размера, а не весь лимит результата за один запрос.
SEARCH_PAGE_SIZE = 100
SEARCH_SCAN_LIMIT = 2000


class CampaignQueries:
    def __init__(
        self,
        repository: CampaignReaderRepository,
        snapshots: CampaignSnapshotRepository | None = None,
    ) -> None:
        self._repository = repository
        self._snapshots = snapshots

    async def search(self, query: str, limit: int) -> list[Campaign]:
        """Находит кампанию по ID (числовой запрос) или по части названия."""
        query = query.strip()
        if not query:
            return await self._repository.list_campaigns(limit)
        if query.isdigit():
            try:
                return [await self._repository.get_campaign(int(query))]
            except RepositoryNotFoundError:
                return []

        needle = query.casefold()
        matches: list[Campaign] = []
        offset = 0
        while len(matches) < limit and offset < SEARCH_SCAN_LIMIT:
            page = await self._repository.list_campaigns(
                SEARCH_PAGE_SIZE, offset
            )
            matches.extend(
                campaign
                for campaign in page
                if needle in campaign.name.casefold()
            )
            if len(page) < SEARCH_PAGE_SIZE:
                break
            offset += len(page)
        return matches[:limit]

    async def get_with_streams(
        self, campaign_id: int
    ) -> tuple[Campaign, list[Stream]]:
        try:
            campaign = await self._repository.get_campaign(campaign_id)
        except RepositoryNotFoundError as exc:
            raise NotFoundError(
                f"Кампания #{campaign_id} не найдена в Keitaro"
            ) from exc
        streams = await self._repository.list_streams(campaign_id)
        if self._snapshots is not None:
            await self._snapshots.sync(campaign, streams)
            streams = await self._snapshots.list_streams(campaign_id)
        return campaign, streams
