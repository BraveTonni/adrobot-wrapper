"""Журнал операций на SQLAlchemy - реализация ports.AuditLog."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.models import Operation

logger = logging.getLogger(__name__)


class AuditLog:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        *,
        action: str,
        status: str,
        campaign_id: int | None = None,
        stream_id: int | None = None,
        detail: dict[str, object] | None = None,
    ) -> None:
        self._session.add(
            Operation(
                action=action,
                status=status,
                campaign_id=campaign_id,
                stream_id=stream_id,
                detail=detail,
            )
        )
        try:
            await self._session.commit()
        except Exception:
            # Ошибка сценария важнее: не маскируем её сбоем журнала.
            logger.exception("не удалось записать операцию %s", action)
            await self._session.rollback()


async def recent_operations(
    session: AsyncSession, limit: int = 50
) -> list[Operation]:
    result = await session.scalars(
        select(Operation).order_by(Operation.id.desc()).limit(limit)
    )
    return list(result)
