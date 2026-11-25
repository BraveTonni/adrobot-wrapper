import pytest

from app.application.campaigns.creator import CampaignCreator
from app.application.campaigns.editor import CampaignEditor
from app.application.campaigns.queries import CampaignQueries
from app.application.catalog.service import Catalog
from app.application.health.check import HealthCheck
from app.application.operations.history import OperationHistory
from app.config import Settings
from app.core.container import build_container


@pytest.mark.asyncio
async def test_build_container_wires_application_services() -> None:
    config = Settings(
        _env_file=None,
        database_url="sqlite+aiosqlite:///:memory:",
    )
    container = build_container(config)

    try:
        assert container.settings is config
        assert isinstance(container.catalog, Catalog)
        assert isinstance(container.campaign_creator, CampaignCreator)
        assert isinstance(container.campaign_editor, CampaignEditor)
        assert isinstance(container.campaign_queries, CampaignQueries)
        assert isinstance(container.operation_history, OperationHistory)
        assert isinstance(container.health_check, HealthCheck)
    finally:
        await container.close()
