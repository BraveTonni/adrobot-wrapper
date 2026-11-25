from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.domain.operations.entities import AuditRecord
from app.infrastructure.persistence.audit import SqlAuditRepository
from app.infrastructure.persistence.models import Operation


def session_factory(session: AsyncMock) -> tuple[MagicMock, MagicMock]:
    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=session)
    context_manager.__aexit__ = AsyncMock(return_value=None)
    return MagicMock(return_value=context_manager), context_manager


@pytest.mark.asyncio
async def test_begin_commits_pending_operation() -> None:
    session = AsyncMock()
    session.add = MagicMock(
        side_effect=lambda operation: setattr(operation, "id", 1)
    )
    factory, context_manager = session_factory(session)
    repository = SqlAuditRepository(factory)

    operation_id = await repository.begin(
        action="campaign.create",
        campaign_id=3,
        detail={"geo": "US"},
    )

    operation = session.add.call_args.args[0]
    assert operation_id == 1
    assert isinstance(operation, Operation)
    assert operation.action == "campaign.create"
    assert operation.status == "pending"
    assert operation.actor == "unknown"
    assert operation.entity_type == "operation"
    assert operation.campaign_id == 3
    assert operation.detail == {"geo": "US"}
    session.commit.assert_awaited_once()
    context_manager.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
async def test_begin_rolls_back_and_propagates_commit_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = AsyncMock()
    session.add = MagicMock()
    session.commit.side_effect = SQLAlchemyError("database down")
    factory, _ = session_factory(session)
    repository = SqlAuditRepository(factory)

    with pytest.raises(SQLAlchemyError, match="database down"):
        await repository.begin(action="campaign.create")

    session.rollback.assert_awaited_once()
    assert "не удалось записать операцию" in caplog.text


@pytest.mark.asyncio
async def test_recent_maps_orm_rows_to_domain_records() -> None:
    operation = Operation(
        id=1,
        created_at=datetime(2026, 1, 2, tzinfo=UTC),
        action="campaign.create",
        campaign_id=7,
        stream_id=None,
        status="ok",
        detail={"name": "x"},
        actor="qa-user",
        entity_type="campaign",
        entity_id=7,
        before_payload={"name": "old"},
        after_payload={"name": "x"},
    )
    session = AsyncMock()
    session.scalars.return_value = [operation]
    factory, _ = session_factory(session)
    repository = SqlAuditRepository(factory)

    records = await repository.recent(limit=2)

    assert records == [
        AuditRecord(
            id=1,
            created_at=datetime(2026, 1, 2, tzinfo=UTC),
            action="campaign.create",
            campaign_id=7,
            stream_id=None,
            status="ok",
            detail={"name": "x"},
            actor="qa-user",
            entity_type="campaign",
            entity_id=7,
            before_payload={"name": "old"},
            after_payload={"name": "x"},
        )
    ]
    session.scalars.assert_awaited_once()
