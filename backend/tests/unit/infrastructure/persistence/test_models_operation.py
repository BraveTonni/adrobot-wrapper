from datetime import UTC

from app.infrastructure.persistence.models import Base, Operation
from app.infrastructure.persistence.models.operation import utcnow


def test_operation_maps_audit_fields() -> None:
    operation = Operation(
        action="stream.offer_add",
        campaign_id=2,
        stream_id=3,
        status="ok",
        detail={"offer_id": 4},
    )

    assert Operation.__tablename__ == "audit_log"
    assert operation.action == "stream.offer_add"
    assert operation.stream_id == 3
    assert operation.detail == {"offer_id": 4}
    assert "audit_log" in Base.metadata.tables


def test_utcnow_returns_timezone_aware_utc_time() -> None:
    assert utcnow().tzinfo is UTC
