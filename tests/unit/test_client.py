from __future__ import annotations

import httpx
import pytest

from appflowy_mcp_toolkit.config import AppFlowyConfig
from appflowy_mcp_toolkit.errors import AppFlowyAuthError, AppFlowyError, AppFlowyRateLimitError
from tests.helpers import json_response


def test_list_workspaces_uses_bearer(make_client):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return json_response({"data": [{"workspace_id": "ws_demo_001", "workspace_name": "Demo"}]})

    client = make_client(handler)
    result = client.list_workspaces()

    assert result[0]["workspace_id"] == "ws_demo_001"
    assert seen[0].url.path == "/api/workspace"
    assert seen[0].headers["authorization"] == "Bearer test-token"


def test_get_folder_passes_depth_and_root(make_client):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/workspace/ws_demo_001/folder"
        assert request.url.params["depth"] == "2"
        assert request.url.params["root_view_id"] == "view_demo_001"
        return json_response({"data": {"view_id": "view_demo_001", "children": []}})

    client = make_client(handler)
    assert (
        client.get_folder("ws_demo_001", depth=2, root_view_id="view_demo_001")["view_id"]
        == "view_demo_001"
    )


def test_row_details_joins_ids(make_client):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/workspace/ws/database/db/row/detail"
        assert request.url.params["ids"] == "row1,row2"
        assert request.url.params["with_doc"] == "true"
        return json_response({"data": [{"id": "row1"}, {"id": "row2"}]})

    client = make_client(handler)
    assert len(client.get_database_rows("ws", "db", ["row1", "row2"], with_doc=True)) == 2


def test_auth_error_is_typed(make_client):
    def handler(_request: httpx.Request) -> httpx.Response:
        return json_response({"message": "bad token"}, status_code=401)

    client = make_client(handler)
    with pytest.raises(AppFlowyAuthError):
        client.list_workspaces()


def test_rate_limit_error_preserves_retry_after(make_client):
    def handler(_request: httpx.Request) -> httpx.Response:
        return json_response(
            {"message": "slow down"}, status_code=429, headers={"retry-after": "60"}
        )

    client = make_client(handler)
    with pytest.raises(AppFlowyRateLimitError) as exc:
        client.list_workspaces()
    assert exc.value.retry_after == "60"


def test_refresh_retry_updates_token():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return json_response({"message": "expired"}, status_code=401)
        if request.url.path == "/gotrue/token":
            return json_response({"access_token": "new-token", "refresh_token": "refresh-2"})
        return json_response({"data": []})

    config = AppFlowyConfig(
        base_url="https://example.test",
        access_token="old-token",
        refresh_token="refresh-1",
    )
    client = __import__("appflowy_mcp_toolkit.client", fromlist=["AppFlowyClient"]).AppFlowyClient(
        config,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert client.list_workspaces() == []
    assert requests[-1].headers["authorization"] == "Bearer new-token"


def test_create_database_row_dry_run_does_not_call_network(make_client):
    def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("dry-run should not call network")

    client = make_client(handler)
    result = client.create_database_row(
        "ws_demo_001",
        "db_demo_001",
        cells={"Description": "Test"},
        document="Body",
    )

    assert result["dry_run"] is True
    assert result["method"] == "POST"
    assert result["json"] == {"cells": {"Description": "Test"}, "document": "Body"}


def test_create_database_row_requires_write_flag(make_client):
    client = make_client(lambda _request: json_response({"data": "row_demo_001"}))

    with pytest.raises(AppFlowyError, match="Writes are disabled"):
        client.create_database_row(
            "ws_demo_001",
            "db_demo_001",
            cells={"Description": "Test"},
            dry_run=False,
        )


def test_create_database_row_executes_when_enabled():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return json_response({"data": "row_demo_001", "code": 0})

    config = AppFlowyConfig(
        base_url="https://example.test",
        access_token="test-token",
        allow_writes=True,
    )
    from appflowy_mcp_toolkit.client import AppFlowyClient

    client = AppFlowyClient(
        config,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = client.create_database_row(
        "ws_demo_001",
        "db_demo_001",
        cells={"Description": "Test"},
        dry_run=False,
    )

    assert result["data"] == "row_demo_001"
    assert seen[0].method == "POST"
    assert seen[0].url.path == "/api/workspace/ws_demo_001/database/db_demo_001/row"
