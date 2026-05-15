from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from appflowy_mcp_toolkit.client import AppFlowyClient
from appflowy_mcp_toolkit.config import AppFlowyConfig


@pytest.fixture
def config() -> AppFlowyConfig:
    return AppFlowyConfig(base_url="https://example.test", access_token="test-token")


@pytest.fixture
def make_client(
    config: AppFlowyConfig,
) -> Callable[[Callable[[httpx.Request], httpx.Response]], AppFlowyClient]:
    def factory(handler: Callable[[httpx.Request], httpx.Response]) -> AppFlowyClient:
        return AppFlowyClient(
            config, http_client=httpx.Client(transport=httpx.MockTransport(handler))
        )

    return factory
