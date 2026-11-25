"""Build, create and verify configured campaign streams."""

from collections.abc import Sequence
from typing import Any

from app.application.campaigns.dtos import (
    CampaignStreamDefinition,
    CreateStream,
)
from app.application.errors import ExternalServiceError
from app.application.ports import CampaignStreamsRepository
from app.domain.campaigns.entities import Stream

DEFAULT_CAMPAIGN_STREAMS = (
    CampaignStreamDefinition(
        name="Geo {geo}",
        type="regular",
        schema="redirect",
        position=1,
        action_payload="{geo_redirect_url}",
        filters=({"name": "country", "mode": "accept", "payload": ["{geo}"]},),
    ),
    CampaignStreamDefinition(
        name="Offers",
        type="default",
        schema="landings",
        position=2,
        initial_offer=True,
    ),
)


class CampaignStreamsCreator:
    def __init__(
        self,
        repository: CampaignStreamsRepository,
        definitions: Sequence[
            CampaignStreamDefinition
        ] = DEFAULT_CAMPAIGN_STREAMS,
        *,
        geo_redirect_url: str = "https://google.com",
    ) -> None:
        self._repository = repository
        if not definitions:
            raise ValueError("нужно настроить хотя бы один поток кампании")
        positions = [definition.position for definition in definitions]
        if len(set(positions)) != len(positions):
            raise ValueError("позиции потоков кампании должны быть уникальны")
        if not any(
            definition.schema == "landings" and definition.initial_offer
            for definition in definitions
        ):
            raise ValueError("нужен поток landings с начальным оффером")
        self._definitions = tuple(
            sorted(definitions, key=lambda definition: definition.position)
        )
        self._geo_redirect_url = geo_redirect_url

    async def create(
        self, campaign_id: int, *, geo: str, offer_id: int
    ) -> list[Stream]:
        created: list[Stream] = []
        replacements = {
            "geo": geo,
            "geo_redirect_url": self._geo_redirect_url,
        }
        for definition in self._definitions:
            filters = tuple(
                _replace_values(item, replacements)
                for item in definition.filters
            )
            command = CreateStream(
                campaign_id=campaign_id,
                name=_replace_text(definition.name, replacements),
                type=definition.type,
                schema=definition.schema,
                position=definition.position,
                action_type=definition.action_type,
                action_payload=(
                    _replace_text(definition.action_payload, replacements)
                    if definition.action_payload is not None
                    else None
                ),
                filters=filters,
                offers=(
                    ({"offer_id": offer_id, "share": 100, "state": "active"},)
                    if definition.initial_offer
                    else ()
                ),
            )
            created.append(await self._repository.create_stream(command))

        streams = await self._repository.list_streams(campaign_id)
        order = [stream.id for stream in streams]
        expected_order = [stream.id for stream in created]

        if order != expected_order:
            raise ExternalServiceError(
                f"неожиданный порядок потоков {order}: "
                f"ожидались настроенные потоки {expected_order}"
            )

        return streams


def _replace_text(value: str, replacements: dict[str, str]) -> str:
    for key, replacement in replacements.items():
        value = value.replace("{" + key + "}", replacement)
    return value


def _replace_values(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, str):
        return _replace_text(value, replacements)
    if isinstance(value, list):
        return [_replace_values(item, replacements) for item in value]
    if isinstance(value, dict):
        return {
            key: _replace_values(item, replacements)
            for key, item in value.items()
        }
    return value
