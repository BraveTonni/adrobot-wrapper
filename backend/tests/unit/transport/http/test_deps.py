from types import SimpleNamespace

from app.config import Settings
from app.transport.http.deps import (
    get_campaign_creator,
    get_campaign_editor,
    get_campaign_queries,
    get_catalog,
    get_health_check,
    get_operation_history,
    get_settings,
)


def test_dependencies_resolve_services_from_composition_container() -> None:
    catalog = object()
    creator = object()
    editor = object()
    campaign_queries = object()
    operation_history = object()
    health_check = object()
    config = Settings(_env_file=None)
    container = SimpleNamespace(
        catalog=catalog,
        campaign_creator=creator,
        campaign_editor=editor,
        campaign_queries=campaign_queries,
        operation_history=operation_history,
        health_check=health_check,
        settings=config,
    )
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(container=container))
    )

    assert get_catalog(request) is catalog
    assert get_campaign_creator(request) is creator
    assert get_campaign_editor(request) is editor
    assert get_campaign_queries(request) is campaign_queries
    assert get_operation_history(request) is operation_history
    assert get_health_check(request) is health_check
    assert get_settings(request) is config
