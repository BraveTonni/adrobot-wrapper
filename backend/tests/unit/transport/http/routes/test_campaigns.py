from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.application.campaigns.alias import build_campaign_alias
from app.application.errors import ExternalServiceError
from app.config import Settings
from app.domain.campaigns.entities import Campaign, Stream, StreamOffer
from app.domain.catalog.entities import Offer
from app.transport.http.errors import ApiError
from app.transport.http.routes.campaigns import (
    add_offer,
    cancel_stream_draft,
    create_campaign,
    get_campaign,
    list_campaigns,
    push_stream,
    remove_offer,
    restore_offer,
)
from app.transport.http.schemas.campaigns import CampaignCreate
from app.transport.http.schemas.streams import OfferAdd

KEY = "request-key-1234567890"


def request_with_actor() -> Request:
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/v1/campaigns",
            "raw_path": b"/api/v1/campaigns",
            "query_string": b"",
            "headers": [(b"x-user", b"qa-user")],
            "client": ("127.0.0.1", 1234),
            "server": ("testserver", 80),
        }
    )


def offer_stream() -> Stream:
    return Stream(
        id=10,
        campaign_id=9,
        name="Offers",
        schema="landings",
        offers=[StreamOffer(offer_id=2, share=100)],
    )


def idempotency(
    state: str = "reserved", saved: dict[str, object] | None = None
) -> SimpleNamespace:
    return SimpleNamespace(
        reserve=AsyncMock(return_value=(state, saved)),
        complete=AsyncMock(),
        release=AsyncMock(),
    )


async def call_create(
    creator: SimpleNamespace, idempotency_store: SimpleNamespace
) -> object:
    catalog = SimpleNamespace(offers=AsyncMock(return_value=[Offer(2, "O")]))
    config = Settings(_env_file=None, keitaro_admin_url="https://panel/")
    body = CampaignCreate(
        name="Launch",
        geo="US",
        offer_id=2,
        domain_id=11,
        group_id=12,
        source_id=13,
    )
    return await create_campaign(
        request_with_actor(),
        body,
        creator,
        catalog,
        config,
        idempotency_store,
        idempotency_key=KEY,
    )


@pytest.mark.asyncio
async def test_list_campaigns_passes_search_and_limit_to_query() -> None:
    queries = SimpleNamespace(
        search=AsyncMock(
            return_value=[Campaign(id=1, name="Spring", alias="spring")]
        )
    )
    config = Settings(_env_file=None, campaign_search_limit=23)

    result = await list_campaigns(queries, config, search="SPR")

    assert [item.model_dump() for item in result] == [
        {"id": 1, "name": "Spring", "alias": "spring"}
    ]
    queries.search.assert_awaited_once_with("SPR", 23)


@pytest.mark.asyncio
async def test_create_campaign_passes_validated_options_to_use_case() -> None:
    creator = SimpleNamespace(
        create=AsyncMock(
            return_value=(Campaign(id=9, name="Launch"), [offer_stream()])
        )
    )
    store = idempotency()

    result = await call_create(creator, store)

    assert result.admin_url == "https://panel/#!/campaign.editor/9"
    assert result.streams[0].offers[0].name == "O"
    assert result.warnings == []
    creator.create.assert_awaited_once_with(
        name="Launch",
        alias=build_campaign_alias("Launch", KEY),
        geo="US",
        offer_id=2,
        domain_id=11,
        group_id=12,
        source_id=13,
        actor="qa-user",
        progress=ANY,
    )
    store.complete.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_campaign_requires_idempotency_key() -> None:
    creator = SimpleNamespace(create=AsyncMock())
    store = idempotency()

    with pytest.raises(HTTPException) as caught:
        await create_campaign(
            request_with_actor(),
            CampaignCreate(name="Launch", geo="US", offer_id=2),
            creator,
            SimpleNamespace(offers=AsyncMock(return_value=[])),
            Settings(_env_file=None),
            store,
            idempotency_key=None,
        )

    assert caught.value.status_code == 400
    store.reserve.assert_not_awaited()
    creator.create.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["mismatch", "pending", "stale"])
async def test_create_campaign_explains_reservation_conflicts(
    state: str,
) -> None:
    creator = SimpleNamespace(create=AsyncMock())
    store = idempotency(state)

    with pytest.raises(ApiError) as caught:
        await call_create(creator, store)

    assert caught.value.status_code == 409
    assert caught.value.code == f"idempotency_{state}"
    creator.create.assert_not_awaited()
    store.complete.assert_not_awaited()
    store.release.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_campaign_replays_the_completed_response() -> None:
    creator = SimpleNamespace(create=AsyncMock())
    saved = {
        "id": 9,
        "name": "Launch",
        "alias": "launch",
        "admin_url": "https://panel/#!/campaign.editor/9",
        "streams": [],
        "warnings": [],
    }

    result = await call_create(creator, idempotency("complete", saved))

    assert result.id == 9
    creator.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_campaign_releases_reservation_after_a_rollback() -> None:
    creator = SimpleNamespace(
        create=AsyncMock(side_effect=ExternalServiceError("rolled back"))
    )
    store = idempotency()

    with pytest.raises(ExternalServiceError, match="rolled back"):
        await call_create(creator, store)

    store.release.assert_awaited_once_with(KEY)
    store.complete.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("remote_state", ["unknown", "leftover"])
async def test_create_campaign_keeps_reservation_for_unclear_outcome(
    remote_state: str,
) -> None:
    async def fail(**kwargs: object) -> None:
        kwargs["progress"].remote_state = remote_state
        raise ExternalServiceError("outcome unclear")

    creator = SimpleNamespace(create=AsyncMock(side_effect=fail))
    store = idempotency()

    with pytest.raises(ExternalServiceError, match="outcome unclear"):
        await call_create(creator, store)

    store.release.assert_not_awaited()
    store.complete.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_campaign_keeps_cause_when_release_fails() -> None:
    creator = SimpleNamespace(
        create=AsyncMock(side_effect=ExternalServiceError("rolled back"))
    )
    store = idempotency()
    store.release.side_effect = RuntimeError("database unavailable")

    with pytest.raises(ExternalServiceError, match="rolled back"):
        await call_create(creator, store)


@pytest.mark.asyncio
async def test_create_campaign_returns_verification_warnings() -> None:
    async def succeed(**kwargs: object) -> tuple[Campaign, list[Stream]]:
        kwargs["progress"].warnings.append("Keitaro сохранил название как «X»")
        return Campaign(id=9, name="Launch"), [offer_stream()]

    creator = SimpleNamespace(create=AsyncMock(side_effect=succeed))

    result = await call_create(creator, idempotency())

    assert result.warnings == ["Keitaro сохранил название как «X»"]


@pytest.mark.asyncio
async def test_get_campaign_returns_query_result_with_offer_names() -> None:
    campaign = Campaign(id=9, name="Launch")
    queries = SimpleNamespace(
        get_with_streams=AsyncMock(return_value=(campaign, [offer_stream()]))
    )
    catalog = SimpleNamespace(offers=AsyncMock(return_value=[Offer(2, "O")]))
    config = Settings(_env_file=None)

    result = await get_campaign(9, queries, catalog, config)

    assert result.id == 9
    assert result.streams[0].offers[0].name == "O"


@pytest.mark.asyncio
async def test_add_offer_returns_stream_response() -> None:
    editor = SimpleNamespace(add_offer=AsyncMock(return_value=offer_stream()))
    catalog = SimpleNamespace(offers=AsyncMock(return_value=[]))

    result = await add_offer(
        request_with_actor(), 1, 2, OfferAdd(offer_id=3), editor, catalog
    )

    assert result.id == 10
    editor.add_offer.assert_awaited_once_with(1, 2, 3, actor="qa-user")


@pytest.mark.asyncio
async def test_remove_offer_returns_stream_response() -> None:
    editor = SimpleNamespace(
        remove_offer=AsyncMock(return_value=offer_stream())
    )
    catalog = SimpleNamespace(offers=AsyncMock(return_value=[]))

    result = await remove_offer(request_with_actor(), 1, 2, 3, editor, catalog)

    assert result.id == 10
    editor.remove_offer.assert_awaited_once_with(1, 2, 3, actor="qa-user")


@pytest.mark.asyncio
async def test_push_stream_passes_actor_to_editor() -> None:
    editor = SimpleNamespace(push=AsyncMock(return_value=offer_stream()))
    catalog = SimpleNamespace(offers=AsyncMock(return_value=[]))

    result = await push_stream(request_with_actor(), 1, 2, editor, catalog)

    assert result.id == 10
    editor.push.assert_awaited_once_with(1, 2, actor="qa-user")


@pytest.mark.asyncio
async def test_cancel_stream_draft_passes_actor_to_editor() -> None:
    editor = SimpleNamespace(
        cancel_draft=AsyncMock(return_value=offer_stream())
    )
    catalog = SimpleNamespace(offers=AsyncMock(return_value=[]))

    result = await cancel_stream_draft(
        request_with_actor(), 1, 2, editor, catalog
    )

    assert result.id == 10
    editor.cancel_draft.assert_awaited_once_with(1, 2, actor="qa-user")


@pytest.mark.asyncio
async def test_restore_offer_passes_actor_to_editor() -> None:
    editor = SimpleNamespace(
        restore_offer=AsyncMock(return_value=offer_stream())
    )
    catalog = SimpleNamespace(offers=AsyncMock(return_value=[]))

    result = await restore_offer(
        request_with_actor(), 1, 2, 3, editor, catalog
    )

    assert result.id == 10
    editor.restore_offer.assert_awaited_once_with(1, 2, 3, actor="qa-user")
