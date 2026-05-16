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
) -> Callable[[Callable[[httpx.Request], httpx.Response], bool], AppFlowyClient]:
    def factory(
        handler: Callable[[httpx.Request], httpx.Response],
        allow_writes: bool = False,
    ) -> AppFlowyClient:
        test_config = AppFlowyConfig(
            base_url=config.base_url,
            access_token=config.access_token,
            refresh_token=config.refresh_token,
            timeout_seconds=config.timeout_seconds,
            allow_writes=allow_writes,
        )
        return AppFlowyClient(
            test_config, http_client=httpx.Client(transport=httpx.MockTransport(handler))
        )

    return factory
