from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.application.operations.history import OperationHistory
from app.domain.operations.entities import AuditRecord


@pytest.mark.asyncio
async def test_recent_delegates_limit_to_audit_repository() -> None:
    records = [
        AuditRecord(
            id=1,
            created_at=datetime(2026, 1, 2, tzinfo=UTC),
            action="campaign.create",
            campaign_id=2,
            stream_id=None,
            status="ok",
            detail=None,
        )
    ]
    repository = AsyncMock()
    repository.recent.return_value = records

    result = await OperationHistory(repository).recent(limit=5)

    assert result == records
    repository.recent.assert_awaited_once_with(5)
