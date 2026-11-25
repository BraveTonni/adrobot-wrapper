import pytest
from pydantic import ValidationError

from app.transport.http.schemas.streams import OfferAdd


def test_offer_add_accepts_positive_id() -> None:
    assert OfferAdd(offer_id=3).offer_id == 3


def test_offer_add_rejects_non_positive_id() -> None:
    with pytest.raises(ValidationError):
        OfferAdd(offer_id=0)
