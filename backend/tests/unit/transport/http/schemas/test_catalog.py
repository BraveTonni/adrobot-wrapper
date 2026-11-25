from app.transport.http.schemas.catalog import (
    OfferSummaryOut,
    ReferenceOut,
    ReferencesOut,
)


def test_catalog_response_schemas_keep_expected_fields() -> None:
    references = ReferencesOut(
        domains=[ReferenceOut(id=1, name="domain")],
        groups=[ReferenceOut(id=2, name="group")],
        sources=[ReferenceOut(id=3, name="source")],
    )

    assert OfferSummaryOut(id=4, name="offer").model_dump() == {
        "id": 4,
        "name": "offer",
    }
    assert references.model_dump() == {
        "domains": [{"id": 1, "name": "domain"}],
        "groups": [{"id": 2, "name": "group"}],
        "sources": [{"id": 3, "name": "source"}],
    }
