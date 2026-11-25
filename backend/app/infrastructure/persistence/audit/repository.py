"""SQLAlchemy-реализация репозитория истории операций."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.operations.entities import AuditRecord
from app.infrastructure.persistence.models import Operation

logger = logging.getLogger(__name__)


class SqlAuditRepository:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        self._session_factory = session_factory

    async def begin(
        self,
        *,
        action: str,
        actor: str = "unknown",
        entity_type: str = "operation",
        entity_id: int | None = None,
        campaign_id: int | None = None,
        stream_id: int | None = None,
        detail: dict[str, object] | None = None,
        before_payload: dict[str, object] | list[object] | None = None,
    ) -> int:
        async with self._session_factory() as session:
            operation = Operation(
                action=action,
                actor=actor[:150],
                entity_type=entity_type[:40],
                entity_id=entity_id,
                status="pending",
                campaign_id=campaign_id,
                stream_id=stream_id,
                detail=detail,
                before_payload=before_payload,
            )
            session.add(operation)
            try:
                await session.commit()
            except Exception:
                await session.rollback()
                logger.error(
                    "не удалось записать операцию аудита",
                    extra={
                        "action": action,
                        "exception_type": "database_commit_error",
                    },
                )
                raise
            return operation.id

    async def finish(
        self,
        operation_id: int,
        *,
        status: str,
        campaign_id: int | None = None,
        stream_id: int | None = None,
        detail: dict[str, object] | None = None,
        entity_id: int | None = None,
        before_payload: dict[str, object] | list[object] | None = None,
        after_payload: dict[str, object] | list[object] | None = None,
        error: str | None = None,
    ) -> None:
        async with self._session_factory() as session:
            operation = await session.get(Operation, operation_id)
            if operation is None:
                raise RuntimeError(f"Audit operation {operation_id} not found")
            operation.status = status
            if campaign_id is not None:
                operation.campaign_id = campaign_id
            if stream_id is not None:
                operation.stream_id = stream_id
            if entity_id is not None:
                operation.entity_id = entity_id
            if detail is not None:
                operation.detail = detail
            if before_payload is not None:
                operation.before_payload = before_payload
            operation.after_payload = after_payload
            operation.error = error
            await session.commit()

    async def recent(self, limit: int = 50) -> list[AuditRecord]:
        async with self._session_factory() as session:
            result = await session.scalars(
                select(Operation).order_by(Operation.id.desc()).limit(limit)
            )
            return [_to_domain(operation) for operation in result]


def _to_domain(operation: Operation) -> AuditRecord:
    return AuditRecord(
        id=operation.id,
        created_at=operation.created_at,
        action=operation.action,
        campaign_id=operation.campaign_id,
        stream_id=operation.stream_id,
        status=operation.status,
        detail=operation.detail,
        actor=operation.actor,
        entity_type=operation.entity_type,
        entity_id=operation.entity_id,
        before_payload=operation.before_payload,
        after_payload=operation.after_payload,
        error=operation.error,
    )
