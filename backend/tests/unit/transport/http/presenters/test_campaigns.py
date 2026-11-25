from app.domain.campaigns.entities import Campaign, Stream, StreamOffer
from app.domain.catalog.entities import Offer
from app.transport.http.presenters.campaigns import CampaignResponseFactory


def test_stream_maps_keitaro_fields_and_offer_names() -> None:
    stream = Stream(
        id=3,
        campaign_id=2,
        name="Offers",
        type="default",
        schema="landings",
        offers=[StreamOffer(offer_id=4, share=100, state="active")],
    )

    response = CampaignResponseFactory.stream(
        stream, [Offer(id=4, name="Offer")]
    )

    assert response.model_dump(by_alias=True) == {
        "id": 3,
        "name": "Offers",
        "type": "default",
        "schema": "landings",
        "uses_offers": True,
        "offers": [
            {"offer_id": 4, "name": "Offer", "share": 100, "state": "active"}
        ],
    }


def test_campaign_builds_admin_url_and_maps_streams() -> None:
    campaign = Campaign(id=2, name="Spring", alias="spring")
    stream = Stream(
        id=3,
        campaign_id=2,
        name="Offers",
        schema="landings",
        offers=[StreamOffer(offer_id=4, share=100)],
    )

    response = CampaignResponseFactory.campaign(
        campaign, [stream], [Offer(id=4, name="Offer")], "https://admin/"
    )

    assert response.admin_url == "https://admin/#!/campaign.editor/2"
    assert response.streams[0].offers[0].name == "Offer"
