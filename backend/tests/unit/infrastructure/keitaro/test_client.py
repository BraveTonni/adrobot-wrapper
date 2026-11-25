from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio
import respx

from app.config import Settings
from app.infrastructure.keitaro.client import KeitaroClient
from app.infrastructure.keitaro.errors import KeitaroError
from app.infrastructure.keitaro.schemas import CampaignCreate, StreamCreate


@pytest_asyncio.fixture
async def client() -> AsyncIterator[KeitaroClient]:
    api_client = KeitaroClient(
        Settings(
            _env_file=None,
            keitaro_url="https://keitaro.test/admin_api/v1",
            keitaro_api_key="test-key",
        )
    )
    yield api_client
    await api_client.aclose()


@pytest.mark.asyncio
async def test_list_campaigns_sends_api_key_and_parses_response(
    client: KeitaroClient,
) -> None:
    with respx.mock(base_url="https://keitaro.test/admin_api/v1") as routes:
        route = routes.get("/campaigns").mock(
            return_value=httpx.Response(
                200,
                json={"data": [{"id": 4, "name": "Campaign", "extra": 1}]},
            )
        )

        result = await client.list_campaigns(25)

    request = route.calls.last.request
    assert result[0].name == "Campaign"
    assert request.headers["Api-Key"] == "test-key"
    assert request.url.params["limit"] == "25"


@pytest.mark.asyncio
async def test_get_campaign_accepts_single_item_response(
    client: KeitaroClient,
) -> None:
    with respx.mock(base_url="https://keitaro.test/admin_api/v1") as routes:
        route = routes.get("/campaigns/4").mock(
            return_value=httpx.Response(
                200, json=[{"id": 4, "name": "Campaign"}]
            )
        )

        result = await client.get_campaign(4)

    assert result.id == 4
    assert route.called


@pytest.mark.asyncio
async def test_get_retries_after_tls_connection_timeout(
    client: KeitaroClient,
) -> None:
    with respx.mock(base_url="https://keitaro.test/admin_api/v1") as routes:
        route = routes.get("/domains").mock(
            side_effect=[
                httpx.ConnectTimeout("TLS handshake timed out"),
                httpx.Response(200, json=[{"id": 1, "name": "domain"}]),
            ]
        )

        result = await client.list_domains()

    assert result[0].name == "domain"
    assert route.call_count == 2


@pytest.mark.asyncio
async def test_get_retries_transient_upstream_server_error(
    client: KeitaroClient,
) -> None:
    with respx.mock(base_url="https://keitaro.test/admin_api/v1") as routes:
        route = routes.get("/domains").mock(
            side_effect=[
                httpx.Response(502),
                httpx.Response(200, json=[{"id": 1, "name": "domain"}]),
            ]
        )

        result = await client.list_domains()

    assert result[0].name == "domain"
    assert route.call_count == 2


@pytest.mark.asyncio
async def test_create_campaign_posts_api_payload(
    client: KeitaroClient,
) -> None:
    payload = CampaignCreate(
        name="New",
        alias="new-123456789abc",
        domain_id=1,
        group_id=2,
        traffic_source_id=3,
    )
    with respx.mock(base_url="https://keitaro.test/admin_api/v1") as routes:
        route = routes.post("/campaigns").mock(
            return_value=httpx.Response(201, json={"id": 5, "name": "New"})
        )

        result = await client.create_campaign(payload)

    assert result.id == 5
    assert route.calls.last.request.read() == (
        b'{"name":"New","alias":"new-123456789abc",'
        b'"type":"position","domain_id":1,'
        b'"group_id":2,"traffic_source_id":3}'
    )


@pytest.mark.asyncio
async def test_create_stream_posts_stream_data(client: KeitaroClient) -> None:
    with respx.mock(base_url="https://keitaro.test/admin_api/v1") as routes:
        create_route = routes.post("/streams").mock(
            return_value=httpx.Response(
                201,
                json={"id": 6, "campaign_id": 5, "schema": "redirect"},
            )
        )
        result = await client.create_stream(
            StreamCreate(
                campaign_id=5,
                name="Geo",
                type="regular",
                schema="redirect",
                position=1,
                action_type="http",
            )
        )

    assert result.id == 6
    assert create_route.called


@pytest.mark.asyncio
async def test_update_stream_puts_stream_changes(
    client: KeitaroClient,
) -> None:
    with respx.mock(base_url="https://keitaro.test/admin_api/v1") as routes:
        update_route = routes.put("/streams/6").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": 6,
                    "campaign_id": 5,
                    "schema": "landings",
                    "offers": [],
                },
            )
        )

        result = await client.update_stream(6, {"offers": []})

    assert result.schema_ == "landings"
    assert update_route.called


@pytest.mark.asyncio
async def test_delete_campaign_accepts_empty_success_response(
    client: KeitaroClient,
) -> None:
    with respx.mock(base_url="https://keitaro.test/admin_api/v1") as routes:
        route = routes.delete("/campaigns/5").mock(
            return_value=httpx.Response(204)
        )

        await client.delete_campaign(5)

    assert route.called


@pytest.mark.asyncio
async def test_list_streams_parses_campaign_streams(
    client: KeitaroClient,
) -> None:
    with respx.mock(base_url="https://keitaro.test/admin_api/v1") as routes:
        route = routes.get("/campaigns/4/streams").mock(
            return_value=httpx.Response(
                200, json=[{"id": 2, "campaign_id": 4}]
            )
        )

        result = await client.list_streams(4)

    assert result[0].id == 2
    assert route.called


@pytest.mark.asyncio
async def test_list_offers_parses_offer_array(client: KeitaroClient) -> None:
    with respx.mock(base_url="https://keitaro.test/admin_api/v1") as routes:
        route = routes.get("/offers").mock(
            return_value=httpx.Response(200, json=[{"id": 3, "name": "Offer"}])
        )

        result = await client.list_offers()

    assert result[0].id == 3
    assert route.called


@pytest.mark.asyncio
async def test_list_domains_parses_domain_array(client: KeitaroClient) -> None:
    with respx.mock(base_url="https://keitaro.test/admin_api/v1") as routes:
        route = routes.get("/domains").mock(
            return_value=httpx.Response(200, json=[{"id": 4, "name": "D"}])
        )

        result = await client.list_domains()

    assert result[0].id == 4
    assert route.called


@pytest.mark.asyncio
async def test_list_groups_parses_group_array(client: KeitaroClient) -> None:
    with respx.mock(base_url="https://keitaro.test/admin_api/v1") as routes:
        route = routes.get("/groups").mock(
            return_value=httpx.Response(200, json=[{"id": 5, "name": "G"}])
        )

        result = await client.list_groups()

    assert result[0].id == 5
    assert route.calls.last.request.url.params["type"] == "campaigns"


@pytest.mark.asyncio
async def test_list_sources_parses_source_array(client: KeitaroClient) -> None:
    with respx.mock(base_url="https://keitaro.test/admin_api/v1") as routes:
        route = routes.get("/traffic_sources").mock(
            return_value=httpx.Response(200, json=[{"id": 6, "name": "S"}])
        )

        result = await client.list_sources()

    assert result[0].id == 6
    assert route.called


@pytest.mark.asyncio
async def test_http_failure_preserves_upstream_status(
    client: KeitaroClient,
) -> None:
    with respx.mock(base_url="https://keitaro.test/admin_api/v1") as routes:
        routes.get("/campaigns").mock(
            return_value=httpx.Response(503, text="maintenance")
        )

        with pytest.raises(KeitaroError, match="HTTP 503") as error:
            await client.list_campaigns(10)

    assert error.value.status == 503
    assert "maintenance" not in str(error.value)


@pytest.mark.asyncio
async def test_invalid_json_response_raises_keitaro_error(
    client: KeitaroClient,
) -> None:
    with respx.mock(base_url="https://keitaro.test/admin_api/v1") as routes:
        routes.get("/campaigns").mock(
            return_value=httpx.Response(
                200,
                content=b"not json",
                headers={"content-type": "application/json"},
            )
        )

        with pytest.raises(KeitaroError, match="некорректный JSON"):
            await client.list_campaigns(10)


@pytest.mark.asyncio
async def test_network_failure_raises_keitaro_error(
    client: KeitaroClient,
) -> None:
    with respx.mock(base_url="https://keitaro.test/admin_api/v1") as routes:
        routes.get("/campaigns").mock(
            side_effect=httpx.ConnectError("offline")
        )

        with pytest.raises(KeitaroError, match="недоступен"):
            await client.list_campaigns(10)
