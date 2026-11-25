import pytest

from app.infrastructure.persistence.database import (
    build_engine,
    build_session_factory,
)


@pytest.mark.asyncio
async def test_engine_and_session_factory_use_configured_database() -> None:
    engine = build_engine("sqlite+aiosqlite:///:memory:")
    factory = build_session_factory(engine)

    async with factory() as session:
        assert session.bind is engine
        assert not session.sync_session.expire_on_commit

    await engine.dispose()


def test_engine_defaults_to_configured_database(monkeypatch) -> None:
    from app.infrastructure.persistence.database import session

    monkeypatch.setattr(
        session.settings, "database_url", "sqlite+aiosqlite:///:memory:"
    )
    engine = build_engine()

    assert engine.url.drivername == "sqlite+aiosqlite"
    assert engine.url.database == ":memory:"
