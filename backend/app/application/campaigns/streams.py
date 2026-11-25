"""Настройка и проверка потоков новой кампании."""

from app.application.errors import ExternalServiceError
from app.application.ports import CampaignStreamsRepository
from app.domain.campaigns.entities import Stream


class CampaignStreamsCreator:
    def __init__(self, repository: CampaignStreamsRepository) -> None:
        self._repository = repository

    async def create(
        self, campaign_id: int, *, geo: str, offer_id: int
    ) -> list[Stream]:
        geo_stream = await self._repository.create_geo_stream(campaign_id, geo)
        offer_stream = await self._repository.create_offer_stream(
            campaign_id, offer_id
        )
        streams = await self._repository.list_streams(campaign_id)
        order = [stream.id for stream in streams]

        if order[:2] != [geo_stream.id, offer_stream.id]:
            raise ExternalServiceError(
                f"неожиданный порядок потоков {order}: "
                f"гео-поток {geo_stream.id} должен быть первым"
            )

        return streams
