"""Приёмочные сценарии на собранном приложении.

Настоящий контур HTTP (аутентификация, обработчики ошибок, маршруты), база,
поднятая настоящими Alembic-миграциями, и Keitaro под моками respx.
Внешние сервисы не вызываются.
"""

import json
import logging
import os
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
import respx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.application.campaigns.alias import build_campaign_alias
from app.config import Settings
from app.infrastructure.persistence.database import build_engine
from app.infrastructure.persistence.models import Base
from app.main import create_app

BACKEND = Path(__file__).resolve().parents[2]
KEITARO = "https://keitaro.test/admin_api/v1"
POSTGRES_URL = os.getenv("ACCEPTANCE_DATABASE_URL", "")
TOKEN = "t" * 40
AUTH = {"Authorization": f"Bearer {TOKEN}"}
KEY = "acceptance-key-0001"

CAMPAIGN = {
    "id": 7,
    "name": "Launch",
    "alias": "launch-alias",
    "type": "position",
    "state": "active",
    "domain_id": 11,
    "group_id": 12,
    "traffic_source_id": 13,
}
GEO_STREAM = {
    "id": 21,
    "campaign_id": 7,
    "name": "Geo US",
    "type": "regular",
    "schema": "redirect",
    "position": 1,
    "state": "active",
    "action_type": "http",
    "action_payload": "https://google.com",
    "filters": [{"name": "country", "mode": "accept", "payload": ["US"]}],
}
OFFER_STREAM = {
    "id": 22,
    "campaign_id": 7,
    "name": "Offers",
    "type": "default",
    "schema": "landings",
    "position": 2,
    "state": "active",
    "action_type": "http",
    "offers": [{"offer_id": 5, "share": 100, "state": "active"}],
}
CREATE_BODY = {
    "name": "Launch",
    "geo": "US",
    "offer_id": 5,
    "domain_id": 11,
    "group_id": 12,
    "source_id": 13,
}
Stack = tuple[TestClient, respx.MockRouter]


def api(path: str) -> str:
    return f"/api/v1{path}"


def ok(json_body: object) -> httpx.Response:
    return httpx.Response(200, json=json_body)


def body_of(call: object) -> dict[str, object]:
    return json.loads(call.request.read())  # type: ignore[attr-defined]


def offers(*shares: tuple[int, int]) -> list[dict[str, object]]:
    return [
        {"offer_id": offer_id, "share": share, "state": "active"}
        for offer_id, share in shares
    ]


@pytest.fixture(autouse=True)
def keep_test_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    # Журналы приложения пишутся в файлы; для сценариев достаточно pytest.
    monkeypatch.setattr(
        "app.core.lifespan.setup_logging", lambda level, directory: None
    )


def run_alembic(url: str, *command: str) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *command],
        cwd=BACKEND,
        env={**os.environ, "DATABASE_URL": url},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


async def clear_schema(url: str) -> None:
    """Тесты делят одну схему: каждый начинается с пустых таблиц."""
    engine = build_engine(url)
    try:
        async with engine.begin() as connection:
            tables = ", ".join(sorted(Base.metadata.tables))
            await connection.execute(text(f"TRUNCATE TABLE {tables}"))
    finally:
        await engine.dispose()


@pytest.fixture(scope="module")
def migrated_database(tmp_path_factory: pytest.TempPathFactory) -> Path | None:
    """База, поднятая настоящими миграциями до head.

    По умолчанию это файл SQLite. С переменной ACCEPTANCE_DATABASE_URL
    сценарии выполняются на настоящем PostgreSQL (джоба `postgres` в CI).
    """
    if POSTGRES_URL:
        run_alembic(POSTGRES_URL, "upgrade", "head")
        yield None
        run_alembic(POSTGRES_URL, "downgrade", "base")
        return
    database = tmp_path_factory.mktemp("alembic") / "template.db"
    run_alembic(
        f"sqlite+aiosqlite:///{database.as_posix()}", "upgrade", "head"
    )
    yield database


@pytest.fixture
async def settings(tmp_path: Path, migrated_database: Path | None) -> Settings:
    options: dict[str, object] = {
        "_env_file": None,
        "keitaro_url": KEITARO,
        "keitaro_admin_url": "https://keitaro.test/admin",
        "keitaro_api_key": "keitaro-key",
        "api_access_token": TOKEN,
        "log_directory": tmp_path / "logs",
    }
    if POSTGRES_URL:
        await clear_schema(POSTGRES_URL)
        return Settings(**options, database_url=POSTGRES_URL)
    assert migrated_database is not None
    database = tmp_path / "adrobot.db"
    shutil.copyfile(migrated_database, database)
    return Settings(
        **options, database_url=f"sqlite+aiosqlite:///{database.as_posix()}"
    )


@pytest.fixture
def application(settings: Settings) -> Iterator[FastAPI]:
    root = logging.getLogger()
    handlers = root.handlers[:]
    yield create_app(settings)
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()
    for handler in handlers:
        root.addHandler(handler)


@pytest.fixture
def stack(application: FastAPI) -> Iterator[Stack]:
    # Часть маршрутов регистрируется только чтобы убедиться, что их не вызвали;
    # незакрытые запросы всё равно ловит общий сторож из conftest.
    with respx.mock(base_url=KEITARO, assert_all_called=False) as keitaro:
        with TestClient(application, raise_server_exceptions=False) as http:
            yield http, keitaro


def stub_catalog(keitaro: respx.MockRouter) -> None:
    keitaro.get("/offers").mock(
        return_value=ok([{"id": 5, "name": "Offer 5"}, {"id": 6, "name": "O"}])
    )
    keitaro.get("/domains").mock(return_value=ok([{"id": 11, "name": "D"}]))
    keitaro.get("/groups").mock(return_value=ok([{"id": 12, "name": "G"}]))
    keitaro.get("/traffic_sources").mock(
        return_value=ok([{"id": 13, "name": "S"}])
    )


def stub_creation(keitaro: respx.MockRouter) -> None:
    stored = {**CAMPAIGN, "alias": build_campaign_alias("Launch", KEY)}
    keitaro.post("/campaigns").mock(return_value=ok(stored))
    keitaro.get("/campaigns/7").mock(return_value=ok(stored))
    keitaro.post("/streams").mock(
        side_effect=[ok(GEO_STREAM), ok(OFFER_STREAM)]
    )
    keitaro.get("/campaigns/7/streams").mock(
        return_value=ok([GEO_STREAM, OFFER_STREAM])
    )


def latest_operation(http: TestClient) -> dict[str, object]:
    response = http.get(api("/operations"), headers=AUTH)
    assert response.status_code == 200
    return response.json()[0]


def test_api_requires_a_valid_bearer_token(stack: Stack) -> None:
    http, keitaro = stack

    assert http.get(api("/campaigns")).status_code == 401
    wrong = http.get(api("/campaigns"), headers={"Authorization": "Bearer x"})
    assert wrong.status_code == 401
    assert http.get(api("/health"), headers=AUTH).json() == {"status": "ok"}
    assert keitaro.get("/campaigns").call_count == 0


def test_create_campaign_publishes_streams_and_replays_the_request(
    stack: Stack,
) -> None:
    http, keitaro = stack
    stub_catalog(keitaro)
    stub_creation(keitaro)

    response = http.post(
        api("/campaigns"),
        headers={**AUTH, "Idempotency-Key": KEY},
        json=CREATE_BODY,
    )

    assert response.status_code == 201
    created = response.json()
    assert created["id"] == 7
    assert created["admin_url"] == (
        "https://keitaro.test/admin/#!/campaign.editor/7"
    )
    assert created["warnings"] == []
    assert [stream["id"] for stream in created["streams"]] == [21, 22]
    assert created["streams"][1]["offers"][0]["name"] == "Offer 5"

    campaign_call = keitaro.post("/campaigns").calls.last
    assert campaign_call.request.headers["Api-Key"] == "keitaro-key"
    assert body_of(campaign_call) == {
        "name": "Launch",
        "alias": created["alias"],
        "type": "position",
        "domain_id": 11,
        "group_id": 12,
        "traffic_source_id": 13,
    }
    # Поля id и state Keitaro назначает сам — в запросе их быть не должно.
    request_only = (
        "campaign_id",
        "name",
        "type",
        "schema",
        "position",
        "action_type",
        "action_payload",
        "filters",
        "offers",
    )
    assert [body_of(call) for call in keitaro.post("/streams").calls] == [
        {key: value for key, value in stream.items() if key in request_only}
        for stream in (GEO_STREAM, OFFER_STREAM)
    ]

    replay = http.post(
        api("/campaigns"),
        headers={**AUTH, "Idempotency-Key": KEY},
        json=CREATE_BODY,
    )

    assert replay.status_code == 201
    assert replay.json() == created
    assert keitaro.post("/campaigns").call_count == 1
    assert keitaro.post("/streams").call_count == 2
    assert latest_operation(http)["action"] == "campaign.create"
    assert latest_operation(http)["status"] == "ok"


def test_create_campaign_rejects_unknown_country_with_a_readable_message(
    stack: Stack,
) -> None:
    http, keitaro = stack

    response = http.post(
        api("/campaigns"),
        headers={**AUTH, "Idempotency-Key": KEY},
        json={**CREATE_BODY, "geo": "XX"},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, str)
    assert "geo" in detail
    assert keitaro.post("/campaigns").call_count == 0


def test_create_campaign_requires_an_idempotency_key(stack: Stack) -> None:
    http, keitaro = stack

    response = http.post(api("/campaigns"), headers=AUTH, json=CREATE_BODY)

    assert response.status_code == 400
    assert keitaro.post("/campaigns").call_count == 0


def test_missing_campaign_is_reported_as_404(stack: Stack) -> None:
    http, keitaro = stack
    keitaro.get("/campaigns/999").mock(
        return_value=httpx.Response(404, json={"error": "not found"})
    )

    response = http.get(api("/campaigns/999"), headers=AUTH)

    assert response.status_code == 404
    assert response.json() == {"detail": "Кампания #999 не найдена в Keitaro"}


def test_rolled_back_creation_frees_the_form_for_a_retry(stack: Stack) -> None:
    http, keitaro = stack
    stub_catalog(keitaro)
    stub_creation(keitaro)
    keitaro.post("/streams").mock(
        side_effect=[
            httpx.Response(500, json={"error": "stream rejected"}),
            ok(GEO_STREAM),
            ok(OFFER_STREAM),
        ]
    )
    delete = keitaro.delete("/campaigns/7").mock(return_value=ok(None))
    headers = {**AUTH, "Idempotency-Key": KEY}

    failed = http.post(api("/campaigns"), headers=headers, json=CREATE_BODY)

    assert failed.status_code == 502
    assert delete.call_count == 1
    assert latest_operation(http)["status"] == "rolled_back"

    retried = http.post(api("/campaigns"), headers=headers, json=CREATE_BODY)

    assert retried.status_code == 201
    assert retried.json()["id"] == 7
    assert delete.call_count == 1
    # Повтор заново создаёт кампанию: первый запрос был полностью откатан.
    assert keitaro.post("/campaigns").call_count == 2


def test_unanswered_creation_keeps_the_reservation(stack: Stack) -> None:
    http, keitaro = stack
    stub_catalog(keitaro)
    keitaro.post("/campaigns").mock(side_effect=httpx.ReadTimeout("timed out"))
    delete = keitaro.delete("/campaigns/7").mock(return_value=ok(None))
    headers = {**AUTH, "Idempotency-Key": KEY}

    failed = http.post(api("/campaigns"), headers=headers, json=CREATE_BODY)

    assert failed.status_code == 502
    assert delete.call_count == 0
    assert latest_operation(http)["status"] == "unknown"

    blocked = http.post(api("/campaigns"), headers=headers, json=CREATE_BODY)

    assert blocked.status_code == 409
    assert blocked.json()["code"] == "idempotency_pending"
    assert keitaro.post("/campaigns").call_count == 1


def test_offer_changes_are_published_to_keitaro_immediately(
    stack: Stack,
) -> None:
    http, keitaro = stack
    stub_catalog(keitaro)
    keitaro.get("/campaigns/7").mock(return_value=ok(CAMPAIGN))
    keitaro.get("/campaigns/7/streams").mock(
        return_value=ok([GEO_STREAM, OFFER_STREAM])
    )
    stored = {
        **OFFER_STREAM,
        "created_at": "2026-01-01T00:00:00Z",
    }
    after_add = {**stored, "offers": offers((5, 50), (6, 50))}
    after_remove = {**stored, "offers": offers((5, 100))}
    keitaro.get("/streams/22").mock(
        side_effect=[ok(stored), ok(after_add), ok(after_remove)]
    )
    put = keitaro.put("/streams/22").mock(
        side_effect=[ok(after_add), ok(after_remove)]
    )

    opened = http.get(api("/campaigns/7"), headers=AUTH)

    assert opened.status_code == 200
    assert [stream["id"] for stream in opened.json()["streams"]] == [21, 22]

    added = http.post(
        api("/campaigns/7/streams/22/offers"),
        headers=AUTH,
        json={"offer_id": 6},
    )

    assert added.status_code == 201
    assert [offer["share"] for offer in added.json()["offers"]] == [50, 50]
    sent = body_of(put.calls[0])
    assert sent["name"] == "Offers"
    assert sent["schema"] == "landings"
    assert "id" not in sent
    assert "created_at" not in sent
    assert sent["offers"] == offers((5, 50), (6, 50))

    removed = http.delete(
        api("/campaigns/7/streams/22/offers/6"), headers=AUTH
    )

    assert removed.status_code == 200
    assert [offer["share"] for offer in removed.json()["offers"]] == [100]
    assert body_of(put.calls[1])["offers"] == offers((5, 100))

    last = http.delete(api("/campaigns/7/streams/22/offers/5"), headers=AUTH)

    assert last.status_code == 409
    assert "последний оффер" in last.json()["detail"]
    assert put.call_count == 2


def test_unexpected_failure_returns_a_generic_json_error(
    stack: Stack, monkeypatch: pytest.MonkeyPatch
) -> None:
    http, _ = stack
    queries = http.app.state.container.campaign_queries
    monkeypatch.setattr(
        queries, "search", AsyncMock(side_effect=RuntimeError("boom /private"))
    )

    response = http.get(api("/campaigns"), headers=AUTH)

    assert response.status_code == 500
    assert response.json() == {"detail": "Внутренняя ошибка сервера"}
