from app.domain.campaigns.entities import Stream, StreamOffer
from app.infrastructure.keitaro.mappers.streams import (
    geo_stream_to_keitaro,
    offer_stream_to_keitaro,
    stream_offer_to_domain,
    stream_offer_to_keitaro,
    stream_to_domain,
)
from app.infrastructure.keitaro.schemas import Stream as KeitaroStream
from app.infrastructure.keitaro.schemas import StreamOffer as KeitaroOffer


def test_geo_stream_request_contains_geo_filter_and_redirect() -> None:
    request = geo_stream_to_keitaro(7, "US", "https://go.example")

    assert request.to_api()["action_type"] == "http"
    assert request.to_api()["action_payload"] == "https://go.example"
    assert request.to_api()["filters"] == [
        {"name": "country", "mode": "accept", "payload": ["US"]}
    ]


def test_offer_stream_request_contains_single_full_share_offer() -> None:
    request = offer_stream_to_keitaro(7, 5)

    assert request.to_api()["action_type"] == "http"
    assert request.to_api()["offers"] == [
        {"offer_id": 5, "share": 100, "state": "active"}
    ]


def test_stream_response_maps_to_domain_entity() -> None:
    response = KeitaroStream(
        id=3,
        campaign_id=7,
        schema="landings",
        offers=[KeitaroOffer(offer_id=5, share=100)],
    )

    assert stream_to_domain(response) == Stream(
        id=3,
        campaign_id=7,
        schema="landings",
        offers=[StreamOffer(offer_id=5, share=100)],
    )


def test_stream_offer_mapping_preserves_mutable_metadata_only() -> None:
    response = KeitaroOffer.model_validate(
        {
            "offer_id": 5,
            "share": 10,
            "state": "active",
            "id": 9,
            "custom": "preserved",
        }
    )

    domain_offer = stream_offer_to_domain(response)

    assert domain_offer == StreamOffer(
        offer_id=5,
        share=10,
        state="active",
        metadata={"custom": "preserved"},
    )
    assert stream_offer_to_keitaro(domain_offer) == {
        "custom": "preserved",
        "offer_id": 5,
        "share": 10,
        "state": "active",
    }
