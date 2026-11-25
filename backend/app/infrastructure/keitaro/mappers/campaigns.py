"""Преобразование кампаний между доменом и Keitaro API."""

from app.application.campaigns.dtos import CreateCampaign
from app.domain.campaigns.entities import Campaign
from app.infrastructure.keitaro.schemas import (
    Campaign as KeitaroCampaign,
)
from app.infrastructure.keitaro.schemas import (
    CampaignCreate as KeitaroCampaignCreate,
)


def campaign_to_domain(campaign: KeitaroCampaign) -> Campaign:
    return Campaign(
        id=campaign.id,
        name=campaign.name,
        alias=campaign.alias,
        type=campaign.type,
        state=campaign.state,
        domain_id=campaign.domain_id,
        group_id=campaign.group_id,
        traffic_source_id=campaign.traffic_source_id,
    )


def campaign_create_to_keitaro(
    command: CreateCampaign,
) -> KeitaroCampaignCreate:
    return KeitaroCampaignCreate(
        name=command.name,
        alias=command.alias,
        domain_id=command.domain_id,
        group_id=command.group_id,
        traffic_source_id=command.traffic_source_id,
    )
