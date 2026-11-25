from app.application.catalog.dtos import References
from app.domain.catalog.entities import Offer, Reference
from app.transport.http.presenters.catalog import CatalogResponseFactory


def test_offers_are_rendered_with_public_fields() -> None:
    responses = CatalogResponseFactory.offers([Offer(id=1, name="Offer")])

    assert [response.model_dump() for response in responses] == [
        {"id": 1, "name": "Offer"}
    ]


def test_references_are_rendered_by_group() -> None:
    references = References(
        domains=[Reference(id=1, name="domain")],
        groups=[Reference(id=2, name="group")],
        sources=[Reference(id=3, name="source")],
    )

    response = CatalogResponseFactory.references(references)

    assert response.model_dump() == {
        "domains": [{"id": 1, "name": "domain"}],
        "groups": [{"id": 2, "name": "group"}],
        "sources": [{"id": 3, "name": "source"}],
    }
