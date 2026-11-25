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
        expected_order = [geo_stream.id, offer_stream.id]

        if order != expected_order:
            raise ExternalServiceError(
                f"неожиданный порядок потоков {order}: "
                f"ожидались ровно два потока {expected_order}"
            )

        return streams
