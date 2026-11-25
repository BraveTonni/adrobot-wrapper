"""Test-wide guard against accidental HTTP requests to external services."""

from collections.abc import Iterator

import pytest
import respx


@pytest.fixture(autouse=True)
def reject_unmocked_http(request: pytest.FixtureRequest) -> Iterator[None]:
    if request.node.get_closest_marker("integration") is not None:
        yield
        return

    with respx.mock(assert_all_mocked=True):
        yield
