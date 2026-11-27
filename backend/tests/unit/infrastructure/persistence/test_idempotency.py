from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.infrastructure.persistence.database import (
    build_engine,
    build_session_factory,
)
from app.infrastructure.persistence.idempotency import SqlIdempotencyRepository
from app.infrastructure.persistence.models import Base
from app.infrastructure.persistence.models.idempotency import (
    IdempotencyRecord,
)


@pytest.fixture
async def repository():
    engine = build_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield SqlIdempotencyRepository(build_session_factory(engine))
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_reserve_stores_a_pending_record(repository) -> None:
    state, saved = await repository.reserve("key-1", "hash-1")

    assert (state, saved) == ("reserved", None)


@pytest.mark.asyncio
async def test_reserve_replays_a_completed_response(repository) -> None:
    await repository.reserve("key-1", "hash-1")
    await repository.complete("key-1", {"id": 7})

    assert await repository.reserve("key-1", "hash-1") == (
        "complete",
        {"id": 7},
    )


@pytest.mark.asyncio
async def test_reserve_reports_a_pending_retry(repository) -> None:
    await repository.reserve("key-1", "hash-1")

    assert await repository.reserve("key-1", "hash-1") == ("pending", None)


@pytest.mark.asyncio
async def test_reserve_rejects_the_key_reused_for_another_body(
    repository,
) -> None:
    await repository.reserve("key-1", "hash-1")

    assert await repository.reserve("key-1", "hash-2") == ("mismatch", None)


@pytest.mark.asyncio
async def test_reserve_marks_an_old_pending_record_as_stale(
    repository,
) -> None:
    factory = repository._session_factory
    await repository.reserve("key-1", "hash-1")
    async with factory() as session:
        record = await session.get(IdempotencyRecord, "key-1")
        assert record is not None
        record.created_at = datetime.now(UTC) - timedelta(hours=2)
        await session.commit()

    assert await repository.reserve("key-1", "hash-1") == ("stale", None)


@pytest.mark.asyncio
async def test_release_frees_the_key_for_a_new_attempt(repository) -> None:
    await repository.reserve("key-1", "hash-1")

    await repository.release("key-1")

    assert await repository.reserve("key-1", "hash-1") == ("reserved", None)


@pytest.mark.asyncio
async def test_release_keeps_a_completed_record(repository) -> None:
    await repository.reserve("key-1", "hash-1")
    await repository.complete("key-1", {"id": 7})

    await repository.release("key-1")

    assert await repository.reserve("key-1", "hash-1") == (
        "complete",
        {"id": 7},
    )


@pytest.mark.asyncio
async def test_release_stale_frees_only_an_old_pending_record(
    repository,
) -> None:
    await repository.reserve("key-1", "hash-1")
    assert await repository.release_stale("key-1") is False

    factory = repository._session_factory
    async with factory() as session:
        record = await session.get(IdempotencyRecord, "key-1")
        assert record is not None
        record.created_at = datetime.now(UTC) - timedelta(hours=2)
        await session.commit()

    assert await repository.release_stale("key-1") is True
    assert await repository.release_stale("key-1") is False


@pytest.mark.asyncio
async def test_reserve_prunes_completed_records_past_retention(
    repository,
) -> None:
    factory = repository._session_factory
    for index in range(2):
        await repository.reserve(f"key-{index}", "hash")
        await repository.complete(f"key-{index}", {"id": index})
    async with factory() as session:
        old = await session.get(IdempotencyRecord, "key-0")
        assert old is not None
        old.created_at = datetime.now(UTC) - timedelta(days=31)
        await session.commit()

    await repository.reserve("key-2", "hash")

    async with factory() as session:
        keys = await session.scalars(
            select(IdempotencyRecord.key).order_by(IdempotencyRecord.key)
        )
        assert list(keys) == ["key-1", "key-2"]


@pytest.mark.asyncio
async def test_complete_requires_the_reservation(repository) -> None:
    with pytest.raises(RuntimeError, match="disappeared"):
        await repository.complete("key-1", {"id": 7})


@pytest.mark.asyncio
async def test_every_record_is_scoped_to_its_own_key(repository) -> None:
    await repository.reserve("key-1", "hash-1")
    await repository.complete("key-1", {"id": 7})

    assert await repository.reserve("key-2", "hash-2") == ("reserved", None)
    factory = repository._session_factory
    async with factory() as session:
        assert (
            await session.scalar(
                select(func.count()).select_from(IdempotencyRecord)
            )
            == 2
        )
