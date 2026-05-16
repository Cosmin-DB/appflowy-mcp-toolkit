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


def test_list_select_options_extracts_status_options(make_client):
    def handler(_request: httpx.Request) -> httpx.Response:
        return json_response(
            {
                "data": [
                    {
                        "name": "Status",
                        "type_option": {
                            "content": {
                                "options": [
                                    {"id": "todo", "name": "To Do"},
                                    {"id": "done", "name": "✅ Done"},
                                ]
                            }
                        },
                    }
                ]
            }
        )

    client = make_client(handler)

    assert [item["name"] for item in client.list_select_options("ws", "db")] == [
        "To Do",
        "✅ Done",
    ]


def test_move_managed_task_status_validates_and_verifies():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path.endswith("/fields"):
            return json_response(
                {
                    "data": [
                        {
                            "name": "Status",
                            "type_option": {
                                "content": {
                                    "options": [
                                        {"id": "doing", "name": "Doing"},
                                        {"id": "done", "name": "✅ Done"},
                                    ]
                                }
                            },
                        }
                    ]
                }
            )
        if request.method == "PUT":
            return json_response({"data": "managed_row_001", "code": 0})
        if request.url.path.endswith("/row/detail"):
            return json_response(
                {"data": [{"id": "managed_row_001", "cells": {"Status": "✅ Done"}}]}
            )
        raise AssertionError(str(request.url))

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

    result = client.move_managed_task_status(
        "ws",
        "db",
        task_key="task-1",
        status="✅ Done",
        dry_run=False,
    )

    assert result["data"] == "managed_row_001"
    assert result["verified_row"][0]["cells"]["Status"] == "✅ Done"
    assert any(request.method == "PUT" for request in seen)


# ---------------------------------------------------------------------------
# Collab inspector
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Flat-shape fixture (used for flat/legacy path tests)
# ---------------------------------------------------------------------------
_COLLAB_VIEWS_FLAT: dict = {
    "views": {
        "view_001": {
            "row_orders": ["row_aaa", "row_bbb", "row_ccc"],
        },
        "view_002": {
            "row_orders": [{"id": "row_ddd"}, {"id": "row_eee"}],
        },
    }
}

# Live-shape fixture: the actual response from beta.appflowy.cloud
# after _extract_data strips the outer {"data": ...} envelope.
# Shape: collab.database.views.<view_id>.row_orders
_COLLAB_VIEWS_LIVE: dict = {
    "collab": {
        "database": {
            "views": {
                "view_live_001": {
                    "row_orders": [{"id": "row_aaa"}, {"id": "row_bbb"}],
                },
                "view_live_002": {
                    "row_orders": [{"id": "row_ccc"}],
                },
            }
        }
    }
}


# ---------------------------------------------------------------------------
# collab_type resolution
# ---------------------------------------------------------------------------


def test_collab_type_string_resolved_to_integer(make_client):
    """String collab_type names must be resolved to their integer value."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return json_response({"data": {}})

    client = make_client(handler)
    client.get_collab_json("ws_001", "db_001", collab_type="Database")
    assert seen[0].url.params["collab_type"] == "1"


def test_collab_type_integer_passed_through(make_client):
    """Explicit integer collab_type values must be forwarded unchanged."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return json_response({"data": {}})

    client = make_client(handler)
    client.get_collab_json("ws_001", "db_001", collab_type=4)  # DatabaseRow
    assert seen[0].url.params["collab_type"] == "4"


def test_collab_type_default_is_database_int(make_client):
    """Default collab_type (\"Database\") must send integer 1, not the string."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return json_response({"data": {}})

    client = make_client(handler)
    client.get_collab_json("ws_001", "db_001")
    assert seen[0].url.params["collab_type"] == "1"


def test_collab_type_numeric_string_resolved_to_integer(make_client):
    """Decimal numeric strings like \"1\" (from CLI args) must be accepted."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return json_response({"data": {}})

    client = make_client(handler)
    client.get_collab_json("ws_001", "db_001", collab_type="1")  # CLI-style
    assert seen[0].url.params["collab_type"] == "1"

    seen.clear()
    client.get_collab_json("ws_001", "db_001", collab_type="4")  # DatabaseRow
    assert seen[0].url.params["collab_type"] == "4"


def test_collab_type_unknown_string_raises(make_client):
    from appflowy_mcp_toolkit.errors import AppFlowyError

    client = make_client(lambda _: json_response({"data": {}}))
    with pytest.raises(AppFlowyError, match="Unknown collab_type"):
        client.get_collab_json("ws_001", "db_001", collab_type="NotAType")


# ---------------------------------------------------------------------------
# get_collab_json path / response
# ---------------------------------------------------------------------------


def test_get_collab_json_calls_correct_path(make_client):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return json_response({"data": _COLLAB_VIEWS_FLAT})

    client = make_client(handler)
    result = client.get_collab_json("ws_001", "db_001", collab_type="Database")

    assert seen[0].url.path == "/api/workspace/v1/ws_001/collab/db_001/json"
    assert seen[0].url.params["collab_type"] == "1"  # integer sent, not string
    assert result == _COLLAB_VIEWS_FLAT


# ---------------------------------------------------------------------------
# _extract_row_orders / get_database_row_orders
# ---------------------------------------------------------------------------


def test_get_database_row_orders_live_shape(make_client):
    """Live-shape response (collab.database.views) must be handled correctly."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return json_response({"data": _COLLAB_VIEWS_LIVE})

    client = make_client(handler)
    result = client.get_database_row_orders("ws_001", "db_001")

    assert len(result) == 2
    view_map = {entry["view_id"]: entry["row_orders"] for entry in result}
    assert view_map["view_live_001"] == ["row_aaa", "row_bbb"]
    assert view_map["view_live_002"] == ["row_ccc"]


def test_get_database_row_orders_flat_shape(make_client):
    """Flat-shape response (top-level views dict) must still work."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return json_response({"data": _COLLAB_VIEWS_FLAT})

    client = make_client(handler)
    result = client.get_database_row_orders("ws_001", "db_001")

    assert len(result) == 2
    view_map = {entry["view_id"]: entry["row_orders"] for entry in result}
    assert view_map["view_001"] == ["row_aaa", "row_bbb", "row_ccc"]
    assert view_map["view_002"] == ["row_ddd", "row_eee"]


def test_get_database_row_orders_extracts_string_list(make_client):
    """Original flat-fixture: string and dict row_orders are both normalised."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return json_response({"data": _COLLAB_VIEWS_FLAT})

    client = make_client(handler)
    result = client.get_database_row_orders("ws_001", "db_001")

    assert len(result) == 2
    view_map = {entry["view_id"]: entry["row_orders"] for entry in result}
    assert view_map["view_001"] == ["row_aaa", "row_bbb", "row_ccc"]
    assert view_map["view_002"] == ["row_ddd", "row_eee"]


def test_get_database_row_orders_empty_on_no_views(make_client):
    def handler(_request: httpx.Request) -> httpx.Response:
        return json_response({"data": {"unrelated_key": 42}})

    client = make_client(handler)
    result = client.get_database_row_orders("ws_001", "db_001")
    assert result == []


def test_get_database_row_orders_inline_views_fallback(make_client):
    payload = {
        "database_inline_views": {
            "view_inline_001": {"row_orders": ["row_x", "row_y"]},
        }
    }

    def handler(_request: httpx.Request) -> httpx.Response:
        return json_response({"data": payload})

    client = make_client(handler)
    result = client.get_database_row_orders("ws_001", "db_001")

    assert len(result) == 1
    assert result[0]["view_id"] == "view_inline_001"
    assert result[0]["row_orders"] == ["row_x", "row_y"]
