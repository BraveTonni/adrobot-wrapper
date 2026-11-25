import pytest

from app.domain.campaigns.entities import Stream


@pytest.mark.parametrize(
    ("schema", "uses_offers"), [("landings", True), ("redirect", False)]
)
def test_stream_reports_whether_it_routes_offers(
    schema: str, uses_offers: bool
) -> None:
    stream = Stream(id=1, campaign_id=2, schema=schema)

    assert stream.uses_offers is uses_offers
