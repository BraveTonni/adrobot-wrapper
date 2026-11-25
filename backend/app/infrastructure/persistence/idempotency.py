from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.persistence.models import IdempotencyRecord


class SqlIdempotencyRepository:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        self._session_factory = session_factory

    async def reserve(
        self, key: str, request_hash: str
    ) -> tuple[str, dict[str, object] | None]:
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

    async def complete(
        self, key: str, response: dict[str, object]
    ) -> None:
        async with self._session_factory() as session:
            record = await session.get(IdempotencyRecord, key)
            if record is None:
                raise RuntimeError("Idempotency reservation disappeared")
            record.status = "complete"
            record.response = response
            await session.commit()

    @staticmethod
    def _existing(
        record: IdempotencyRecord, request_hash: str
    ) -> tuple[str, dict[str, object] | None]:
        if record.request_hash != request_hash:
            return "mismatch", None
        if record.status == "complete" and record.response is not None:
            return "complete", record.response
        return "pending", None
