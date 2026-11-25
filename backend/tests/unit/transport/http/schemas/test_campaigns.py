import pytest
from pydantic import ValidationError

from app.transport.http.schemas.campaigns import CampaignCreate


def test_campaign_create_strips_name_and_normalizes_geo() -> None:
    payload = CampaignCreate(name="  Launch  ", geo=" us ", offer_id=4)

    assert payload.name == "Launch"
    assert payload.geo == "US"
    assert payload.domain_id is None


@pytest.mark.parametrize(
    "data",
    [
        {"name": "   ", "geo": "US", "offer_id": 1},
        {"name": "x", "geo": "USA", "offer_id": 1},
        {"name": "x", "geo": "XX", "offer_id": 1},
        {"name": "x", "geo": "US", "offer_id": 0},
        {"name": "x", "geo": "US", "offer_id": 1, "domain_id": 0},
    ],
)
def test_campaign_create_rejects_invalid_fields(
    data: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        CampaignCreate.model_validate(data)


def test_campaign_create_enforces_name_length() -> None:
    with pytest.raises(ValidationError):
        CampaignCreate(name="x" * 256, geo="US", offer_id=1)
