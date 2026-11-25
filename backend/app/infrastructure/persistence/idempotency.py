from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.persistence.models import IdempotencyRecord

_COMPLETED_RETENTION = timedelta(days=30)
_STALE_AFTER = timedelta(hours=1)


class SqlIdempotencyRepository:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        self._session_factory = session_factory

    async def reserve(
        self, key: str, request_hash: str
    ) -> tuple[str, dict[str, object] | None]:
        await self._prune_completed()
        async with self._session_factory() as session:
            record = await session.get(IdempotencyRecord, key)
            if record is not None:
                return self._existing(record, request_hash)

            session.add(
                IdempotencyRecord(
                    key=key,
                    request_hash=request_hash,
                    status="pending",
                )
            )
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                record = await session.get(IdempotencyRecord, key)
                if record is None:
                    raise
                return self._existing(record, request_hash)
        return "reserved", None

    async def complete(self, key: str, response: dict[str, object]) -> None:
        async with self._session_factory() as session:
            record = await session.get(IdempotencyRecord, key)
            if record is None:
                raise RuntimeError("Idempotency reservation disappeared")
            record.status = "complete"
            record.response = response
            await session.commit()

    async def release(self, key: str) -> None:
        """Release a request known to have failed before any remote write."""
        async with self._session_factory() as session:
            record = await session.get(IdempotencyRecord, key)
            if record is not None and record.status == "pending":
                await session.delete(record)
                await session.commit()

    async def release_stale(self, key: str) -> bool:
        """Release a stale key after an operator has reconciled Keitaro."""
        async with self._session_factory() as session:
            record = await session.get(IdempotencyRecord, key)
            if (
                record is None
                or record.status != "pending"
                or self._state(record) != "stale"
            ):
                return False
            await session.delete(record)
            await session.commit()
            return True

    async def _prune_completed(self) -> None:
        cutoff = datetime.now(UTC) - _COMPLETED_RETENTION
        async with self._session_factory() as session:
            await session.execute(
                delete(IdempotencyRecord).where(
                    IdempotencyRecord.status == "complete",
                    IdempotencyRecord.created_at < cutoff,
                )
            )
            await session.commit()

    @staticmethod
    def _existing(
        record: IdempotencyRecord, request_hash: str
    ) -> tuple[str, dict[str, object] | None]:
        if record.request_hash != request_hash:
            return "mismatch", None
        if record.status == "complete" and record.response is not None:
            return "complete", record.response
        return SqlIdempotencyRepository._state(record), None

    @staticmethod
    def _state(record: IdempotencyRecord) -> str:
        created_at = record.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        if datetime.now(UTC) - created_at > _STALE_AFTER:
            return "stale"
        return "pending"
