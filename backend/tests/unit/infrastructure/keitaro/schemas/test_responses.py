from app.infrastructure.keitaro.schemas.responses import (
    Campaign,
    Offer,
    Stream,
    StreamOffer,
)


def test_campaign_response_ignores_new_upstream_fields() -> None:
    campaign = Campaign.model_validate(
        {"id": 1, "name": "test", "new_field": "ignored"}
    )

    assert campaign.name == "test"
    assert "new_field" not in campaign.model_dump()


def test_stream_offer_preserves_unmodeled_response_fields() -> None:
    offer = StreamOffer.model_validate(
        {
            "offer_id": 9,
            "share": 10,
            "state": "active",
            "id": 1,
            "stream_id": 2,
            "custom_field": {"keep": True},
        }
    )

    assert offer.model_dump() == {
        "offer_id": 9,
        "share": 10,
        "state": "active",
        "id": 1,
        "stream_id": 2,
        "custom_field": {"keep": True},
    }


def test_stream_response_defaults_to_an_empty_offer_list() -> None:
    landing_stream = Stream(id=1, campaign_id=2, schema="landings")

    assert landing_stream.schema_ == "landings"
    assert landing_stream.offers == []
    assert Offer(id=1, name="offer").model_dump() == {
        "id": 1,
        "name": "offer",
    }
