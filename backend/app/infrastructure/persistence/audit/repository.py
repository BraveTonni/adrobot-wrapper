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

    async def record(
        self,
        *,
        action: str,
        status: str,
        campaign_id: int | None = None,
        stream_id: int | None = None,
        detail: dict[str, object] | None = None,
    ) -> None:
        async with self._session_factory() as session:
            session.add(
                Operation(
                    action=action,
                    status=status,
                    campaign_id=campaign_id,
                    stream_id=stream_id,
                    detail=detail,
                )
            )
            try:
                await session.commit()
            except Exception:
                logger.exception("не удалось записать операцию %s", action)
                await session.rollback()

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
    )
