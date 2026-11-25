from datetime import UTC, datetime

from app.domain.operations.entities import AuditRecord
from app.transport.http.presenters.operations import OperationResponseFactory


def test_operations_convert_timestamps_to_iso_format() -> None:
    record = AuditRecord(
        id=4,
        created_at=datetime(2026, 1, 2, tzinfo=UTC),
        action="campaign.create",
        campaign_id=7,
        stream_id=None,
        status="ok",
        detail=None,
    )

    responses = OperationResponseFactory.operations([record])

    assert responses[0].created_at == "2026-01-02T00:00:00+00:00"
