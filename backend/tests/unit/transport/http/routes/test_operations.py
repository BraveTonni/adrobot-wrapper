from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.operations.entities import AuditRecord
from app.transport.http.routes.operations import operations


@pytest.mark.asyncio
async def test_operations_returns_recent_records_as_http_models() -> None:
    record = AuditRecord(
        id=1,
        created_at=datetime(2026, 1, 2, 3, 4, tzinfo=UTC),
        action="campaign.create",
        campaign_id=7,
        stream_id=None,
        status="ok",
        detail={"name": "x"},
    )
    history = SimpleNamespace(recent=AsyncMock(return_value=[record]))

    result = await operations(history)

    assert result[0].created_at == "2026-01-02T03:04:00+00:00"
    assert result[0].detail == {"name": "x"}
