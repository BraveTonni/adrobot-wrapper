from app.domain.campaigns.entities import Stream, StreamOffer
from app.infrastructure.keitaro.mappers.streams import (
    stream_offer_to_domain,
    stream_offer_to_keitaro,
    stream_to_domain,
)
from app.infrastructure.keitaro.schemas import Stream as KeitaroStream
from app.infrastructure.keitaro.schemas import StreamOffer as KeitaroOffer


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
        raw_payload={
            "id": 3,
            "campaign_id": 7,
            "schema": "landings",
            "offers": [{"offer_id": 5, "share": 100}],
        },
    )


def test_stream_mapping_keeps_unknown_keitaro_fields_in_raw_payload() -> None:
    response = KeitaroStream.model_validate(
        {
            "id": 3,
            "campaign_id": 7,
            "schema": "landings",
            "filters": [{"name": "country", "mode": "accept"}],
            "traffic_source_id": 17,
        }
    )

    mapped = stream_to_domain(response)

    assert mapped.raw_payload["filters"] == [
        {"name": "country", "mode": "accept"}
    ]
    assert mapped.raw_payload["traffic_source_id"] == 17


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
