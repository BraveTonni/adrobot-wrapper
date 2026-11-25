"""DTO Admin API: запросы и ответы."""

from app.infrastructure.keitaro.schemas.base import KeitaroModel
from app.infrastructure.keitaro.schemas.requests import (
    CampaignCreate,
    StreamCreate,
    StreamFilter,
)
from app.infrastructure.keitaro.schemas.responses import (
    Campaign,
    CampaignGroup,
    Domain,
    Offer,
    Stream,
    StreamOffer,
    TrafficSource,
)

__all__ = [
    "Campaign",
    "CampaignCreate",
    "CampaignGroup",
    "Domain",
    "KeitaroModel",
    "Offer",
    "Stream",
    "StreamCreate",
    "StreamFilter",
    "StreamOffer",
    "TrafficSource",
]
