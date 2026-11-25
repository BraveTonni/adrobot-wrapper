"""Порты, через которые прикладные сценарии обращаются к инфраструктуре."""

from typing import Protocol

from app.application.campaigns.dtos import CreateCampaign
from app.application.catalog.dtos import References
from app.domain.campaigns.entities import Campaign, Stream, StreamOffer
from app.domain.catalog.entities import Offer
from app.domain.operations.entities import AuditRecord


class AuditRepository(Protocol):
    async def begin(
        self,
        *,
        action: str,
        actor: str = "unknown",
        entity_type: str = "operation",
        entity_id: int | None = None,
        campaign_id: int | None = None,
        stream_id: int | None = None,
        detail: dict[str, object] | None = None,
        before_payload: dict[str, object] | list[object] | None = None,
    ) -> int: ...

    async def finish(
        self,
        operation_id: int,
        *,
        status: str,
        campaign_id: int | None = None,
        stream_id: int | None = None,
        detail: dict[str, object] | None = None,
        entity_id: int | None = None,
        before_payload: dict[str, object] | list[object] | None = None,
        after_payload: dict[str, object] | list[object] | None = None,
        error: str | None = None,
    ) -> None: ...

    async def recent(self, limit: int = 50) -> list[AuditRecord]: ...


class OfferReader(Protocol):
    async def get_offer(self, offer_id: int) -> Offer: ...


class CampaignCreationRepository(OfferReader, Protocol):
    async def create_campaign(self, command: CreateCampaign) -> Campaign: ...

    async def delete_campaign(self, campaign_id: int) -> None: ...


class CampaignStreamsRepository(Protocol):
    async def create_geo_stream(
        self, campaign_id: int, geo: str
    ) -> Stream: ...

    async def create_offer_stream(
        self, campaign_id: int, offer_id: int
    ) -> Stream: ...

    async def list_streams(self, campaign_id: int) -> list[Stream]: ...


class CampaignStreamSetup(Protocol):
    async def create(
        self, campaign_id: int, *, geo: str, offer_id: int
    ) -> list[Stream]: ...


class CampaignEditingRepository(OfferReader, Protocol):
    async def get_stream(self, stream_id: int) -> Stream: ...

    async def update_stream(
        self, stream_id: int, offers: list[StreamOffer]
    ) -> Stream: ...


class CampaignReaderRepository(Protocol):
    async def list_campaigns(
        self, limit: int, offset: int = 0
    ) -> list[Campaign]: ...

    async def get_campaign(self, campaign_id: int) -> Campaign: ...

    async def list_streams(self, campaign_id: int) -> list[Stream]: ...


class CatalogRepository(Protocol):
    async def list_offers(self) -> list[Offer]: ...

    async def list_references(self) -> References: ...


class HealthRepository(Protocol):
    async def check_database(self) -> None: ...
