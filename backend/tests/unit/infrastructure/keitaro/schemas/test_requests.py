import pytest
from pydantic import ValidationError

from app.infrastructure.keitaro.schemas.requests import (
    CampaignCreate,
    StreamCreate,
    StreamFilter,
)


def test_campaign_request_serializes_default_type() -> None:
    payload = CampaignCreate(
        name="campaign", domain_id=1, group_id=2, traffic_source_id=3
    )

    assert payload.to_api() == {
        "name": "campaign",
        "type": "position",
        "domain_id": 1,
        "group_id": 2,
        "traffic_source_id": 3,
    }


def test_stream_request_uses_api_alias_and_omits_empty_fields() -> None:
    payload = StreamCreate(
        campaign_id=1,
        name="Geo US",
        type="regular",
        schema="redirect",
        filters=[StreamFilter(name="country", mode="accept", payload=["US"])],
    )

    assert payload.to_api() == {
        "campaign_id": 1,
        "name": "Geo US",
        "type": "regular",
        "schema": "redirect",
        "filters": [{"name": "country", "mode": "accept", "payload": ["US"]}],
    }


def test_stream_request_rejects_unsupported_type() -> None:
    with pytest.raises(ValidationError):
        StreamCreate(
            campaign_id=1,
            name="bad",
            type="unsupported",
            schema="redirect",
        )
