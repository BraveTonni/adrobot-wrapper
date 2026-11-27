"""Миграции и репозитории на настоящем PostgreSQL.

Тестам нужна переменная TEST_DATABASE_URL (джоба `postgres` в CI). Без неё
они пропускаются, поэтому локальный прогон ничего не требует.
"""

import asyncio
import os
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import inspect

from app.application.catalog.dtos import References
from app.domain.campaigns.entities import Campaign, Stream, StreamOffer
from app.domain.catalog.entities import Offer, Reference
from app.infrastructure.persistence.audit import SqlAuditRepository
from app.infrastructure.persistence.campaigns import (
    SqlCampaignSnapshotRepository,
)
from app.infrastructure.persistence.database import (
    build_engine,
    build_session_factory,
)
from app.infrastructure.persistence.idempotency import SqlIdempotencyRepository
from app.infrastructure.persistence.models import Base
from app.infrastructure.repositories.catalog.cached import (
    CachedCatalogRepository,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

BACKEND = Path(__file__).resolve().parents[3]


def alembic(url: str, *command: str) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *command],
        cwd=BACKEND,
        env={**os.environ, "DATABASE_URL": url},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


@pytest.fixture(scope="module")
def database_url() -> Iterator[str]:
    url = os.getenv("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL tests")
    alembic(url, "upgrade", "head")
    yield url
    alembic(url, "downgrade", "base")


@pytest.fixture
async def session_factory(database_url: str) -> AsyncIterator[object]:
    engine = build_engine(database_url)
    try:
        yield build_session_factory(engine)
    finally:
        await engine.dispose()


async def table_names(session_factory) -> set[str]:
    engine = session_factory.kw["bind"]
    async with engine.connect() as connection:
        names = await connection.run_sync(
            lambda sync_connection: inspect(sync_connection).get_table_names()
        )
    return set(names) - {"alembic_version"}


def fresh_id() -> int:
    # Разные тесты модуля работают с одной базой: ключи не должны пересекаться.
    return int.from_bytes(os.urandom(4), "big") % 2_000_000_000 + 1


async def test_migrations_create_every_application_table(
    session_factory,
) -> None:
    assert await table_names(session_factory) == set(Base.metadata.tables)


async def test_snapshot_repository_round_trips_json_on_postgres(
    session_factory,
) -> None:
    snapshots = SqlCampaignSnapshotRepository(session_factory)
    campaign_id = fresh_id()
    campaign = Campaign(id=campaign_id, name="Кампания", alias="campaign")
    stream = Stream(
        id=campaign_id + 1,
        campaign_id=campaign_id,
        name="Offers",
        type="default",
        schema="landings",
        position=2,
        raw_payload={
            "schema": "landings",
            "filters": [{"name": "country", "mode": "accept"}],
        },
        offers=[
            StreamOffer(
                offer_id=5,
                share=60,
                state="active",
                is_pinned=True,
                published_share=100,
                draft_share=60,
                metadata={"custom": "значение", "tags": [1, 2]},
            )
        ],
    )

    await snapshots.save(campaign, [stream])

    stored = await snapshots.get_stream(campaign_id, stream.id)
    assert stored.raw_payload["filters"] == stream.raw_payload["filters"]
    assert stored.offers[0].metadata == {"custom": "значение", "tags": [1, 2]}
    assert stored.offers[0].published_share == 100
    assert stored.offers[0].is_pinned

    await snapshots.sync(
        campaign,
        [
            Stream(
                id=stream.id,
                campaign_id=campaign_id,
                name="Offers",
                schema="landings",
                position=2,
                offers=[
                    StreamOffer(offer_id=5, share=50),
                    StreamOffer(offer_id=6, share=50),
                ],
            )
        ],
    )

    synced = await snapshots.get_stream(campaign_id, stream.id)
    assert [offer.offer_id for offer in synced.offers] == [5, 6]


async def test_idempotency_admits_a_single_concurrent_reservation(
    session_factory,
) -> None:
    repository = SqlIdempotencyRepository(session_factory)
    key = f"pg-key-{fresh_id()}"

    results = await asyncio.gather(
        *(repository.reserve(key, "hash") for _ in range(5))
    )

    states = sorted(state for state, _ in results)
    assert states == ["pending"] * 4 + ["reserved"]

    await repository.complete(key, {"id": fresh_id()})
    assert (await repository.reserve(key, "hash"))[0] == "complete"

    # Освобождение возвращает ключ только для незавершённой записи.
    pending_key = f"pg-key-{fresh_id()}"
    await repository.reserve(pending_key, "hash")
    await repository.release(pending_key)
    assert await repository.reserve(pending_key, "hash") == ("reserved", None)


async def test_audit_repository_keeps_payloads_and_history(
    session_factory,
) -> None:
    repository = SqlAuditRepository(session_factory)
    campaign_id = fresh_id()

    operation_id = await repository.begin(
        action="campaign.create",
        actor="qa-user",
        entity_type="campaign",
        detail={"name": "Кампания", "geo": ["US", "DE"]},
    )
    await repository.finish(
        operation_id,
        status="rolled_back",
        campaign_id=campaign_id,
        entity_id=campaign_id,
        before_payload={"offers": [{"offer_id": 5}]},
        after_payload=None,
        error="stream setup failed",
    )

    record = (await repository.recent(limit=1))[0]
    assert record.id == operation_id
    assert record.action == "campaign.create"
    assert record.status == "rolled_back"
    assert record.actor == "qa-user"
    assert record.campaign_id == campaign_id
    assert record.detail == {"name": "Кампания", "geo": ["US", "DE"]}
    assert record.before_payload == {"offers": [{"offer_id": 5}]}
    assert record.error == "stream setup failed"


async def test_catalog_cache_reuses_what_an_earlier_instance_stored(
    session_factory,
) -> None:
    references = References(
        domains=[Reference(id=11, name="Домен")],
        groups=[Reference(id=12, name="FORTESTS")],
        sources=[Reference(id=13, name="FORTESTS")],
    )
    first_loader = AsyncMock()
    first_loader.list_offers.return_value = [Offer(id=5, name="Оффер")]
    first_loader.list_references.return_value = references
    first = CachedCatalogRepository(
        first_loader,
        offers_ttl=300,
        references_ttl=300,
        session_factory=session_factory,
    )
    await first.list_offers()
    await first.list_references()

    second_loader = AsyncMock()
    second = CachedCatalogRepository(
        second_loader,
        offers_ttl=300,
        references_ttl=300,
        session_factory=session_factory,
    )

    assert await second.list_offers() == [Offer(id=5, name="Оффер")]
    assert await second.list_references() == references
    second_loader.list_offers.assert_not_awaited()
    second_loader.list_references.assert_not_awaited()
