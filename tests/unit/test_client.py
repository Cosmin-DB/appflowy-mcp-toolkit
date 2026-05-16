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


def test_workspace_settings_uses_settings_route(make_client):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/workspace/ws_demo_001/settings"
        return json_response({"data": {"workspace_id": "ws_demo_001", "name": "Demo"}})

    client = make_client(handler)

    assert client.get_workspace_settings("ws_demo_001") == {
        "workspace_id": "ws_demo_001",
        "name": "Demo",
    }


def test_workspace_members_uses_member_route(make_client):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/workspace/ws_demo_001/member"
        return json_response(
            {"data": {"members": [{"email": "demo@example.test", "role": "owner"}]}}
        )

    client = make_client(handler)

    assert client.list_workspace_members("ws_demo_001") == [
        {"email": "demo@example.test", "role": "owner"}
    ]


def test_workspace_usage_uses_usage_route(make_client):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/workspace/ws_demo_001/usage"
        return json_response({"data": {"member_count": 1, "storage_bytes": 1024}})

    client = make_client(handler)

    assert client.get_workspace_usage("ws_demo_001") == {
        "member_count": 1,
        "storage_bytes": 1024,
    }


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


def test_navigation_view_lists_use_workspace_routes(make_client):
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return json_response({"data": [{"view_id": request.url.path.rsplit("/", 1)[-1]}]})

    client = make_client(handler)

    assert client.list_recent_views("ws") == [{"view_id": "recent"}]
    assert client.list_favorite_views("ws") == [{"view_id": "favorite"}]
    assert client.list_trash_views("ws") == [{"view_id": "trash"}]
    assert seen == [
        "/api/workspace/ws/recent",
        "/api/workspace/ws/favorite",
        "/api/workspace/ws/trash",
    ]


def test_row_details_joins_ids(make_client):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/workspace/ws/database/db/row/detail"
        assert request.url.params["ids"] == "row1,row2"
        assert request.url.params["with_doc"] == "true"
        return json_response({"data": [{"id": "row1"}, {"id": "row2"}]})

    client = make_client(handler)
    assert len(client.get_database_rows("ws", "db", ["row1", "row2"], with_doc=True)) == 2


def test_list_updated_database_rows_passes_after(make_client):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/workspace/ws/database/db/row/updated"
        assert request.url.params["after"] == "2026-05-16T10:00:00Z"
        return json_response({"data": [{"row_id": "row1", "updated_at": "2026-05-16T10:01:00Z"}]})

    client = make_client(handler)

    result = client.list_updated_database_rows("ws", "db", after="2026-05-16T10:00:00Z")

    assert result == [{"row_id": "row1", "updated_at": "2026-05-16T10:01:00Z"}]


def test_list_updated_database_rows_can_use_server_default(make_client):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/workspace/ws/database/db/row/updated"
        assert "after" not in request.url.params
        return json_response({"data": []})

    client = make_client(handler)

    assert client.list_updated_database_rows("ws", "db") == []


def test_search_documents_passes_stable_query_params(make_client):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/search/ws"
        assert request.url.params["query"] == "roadmap"
        assert request.url.params["limit"] == "5"
        assert request.url.params["preview_size"] == "120"
        assert request.url.params["score"] == "0.4"
        return json_response(
            {
                "data": [
                    {
                        "object_id": "page1",
                        "workspace_id": "ws",
                        "score": 0.72,
                        "content_type": 0,
                        "content": "full indexed content",
                        "preview": "indexed content",
                        "created_by": "Cosmin",
                        "created_at": "2026-05-16T10:00:00Z",
                    }
                ]
            }
        )

    client = make_client(handler)

    result = client.search_documents(
        "ws",
        "roadmap",
        limit=5,
        preview_size=120,
        score=0.4,
    )

    assert result[0]["object_id"] == "page1"


def test_search_documents_can_use_server_defaults(make_client):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/search/ws"
        assert request.url.params["query"] == "roadmap"
        assert "limit" not in request.url.params
        assert "preview_size" not in request.url.params
        assert "score" not in request.url.params
        return json_response({"data": []})

    client = make_client(handler)

    assert client.search_documents("ws", "roadmap") == []


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


def test_create_database_row_verified_dry_run_describes_checks(make_client):
    client = make_client(lambda _request: json_response({"data": "unused"}))

    result = client.create_database_row_verified(
        "ws_demo_001",
        "db_demo_001",
        cells={"Description": "Test"},
    )

    assert result["dry_run"] is True
    assert "REST row list" in result["verification"]["would_check"]
    assert "database row_orders" in result["verification"]["would_check"]


def test_verify_database_row_uses_data_plane_signals():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        path = request.url.path
        if path == "/api/workspace/ws/database/db/row":
            return json_response({"data": [{"id": "row-target"}]})
        if path == "/api/workspace/ws/database/db/row/detail":
            return json_response({"data": [{"id": "row-target", "cells": {"Description": "T"}}]})
        if path == "/api/workspace/v1/ws/collab/db/json":
            return json_response(
                {
                    "data": {
                        "collab": {
                            "database": {
                                "views": {
                                    "view_board": {
                                        "row_orders": [{"id": "row-target"}],
                                    }
                                }
                            }
                        }
                    }
                }
            )
        if path == "/api/workspace/v1/ws/collab/row-target/json":
            return json_response({"data": {"collab": {"database_row": {"data": {}}}}})
        raise AssertionError(path)

    config = AppFlowyConfig(
        base_url="https://example.test",
        access_token="test-token",
    )
    from appflowy_mcp_toolkit.client import AppFlowyClient

    client = AppFlowyClient(
        config,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = client.verify_database_row("ws", "db", "row-target", include_blob_diff=False)

    assert result["verified"] is True
    assert result["rest_row_list_present"] is True
    assert result["rest_row_detail_present"] is True
    assert result["row_orders_present"] is True
    assert result["views_containing_row"] == ["view_board"]
    assert result["database_row_collab_present"] is True
    assert any(request.url.params.get("collab_type") == "4" for request in seen)


def test_create_database_row_verified_executes_then_verifies():
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path == "/api/workspace/ws/database/db/row":
            return json_response({"data": "row-created", "code": 0})
        if request.method == "GET" and path == "/api/workspace/ws/database/db/row":
            return json_response({"data": [{"id": "row-created"}]})
        if path == "/api/workspace/ws/database/db/row/detail":
            return json_response({"data": [{"id": "row-created"}]})
        if path == "/api/workspace/v1/ws/collab/db/json":
            return json_response(
                {
                    "data": {
                        "views": {
                            "view_001": {
                                "row_orders": ["row-created"],
                            }
                        }
                    }
                }
            )
        if path == "/api/workspace/v1/ws/collab/row-created/json":
            return json_response({"data": {"collab": {"database_row": {}}}})
        raise AssertionError(path)

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

    result = client.create_database_row_verified(
        "ws",
        "db",
        cells={"Description": "Created"},
        dry_run=False,
        include_blob_diff=False,
    )

    assert result["create"]["data"] == "row-created"
    assert result["verification"]["verified"] is True


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
        if request.method == "GET" and request.url.path == "/api/workspace/ws/database/db/row":
            return json_response({"data": [{"id": "managed_row_001"}]})
        if request.url.path.endswith("/row/detail"):
            return json_response(
                {"data": [{"id": "managed_row_001", "cells": {"Status": "✅ Done"}}]}
            )
        if request.url.path == "/api/workspace/v1/ws/collab/db/json":
            return json_response(
                {"data": {"views": {"view_001": {"row_orders": ["managed_row_001"]}}}}
            )
        if request.url.path == "/api/workspace/v1/ws/collab/managed_row_001/json":
            return json_response({"data": {"collab": {"database_row": {}}}})
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
    assert result["verification"]["verified"] is True
    assert any(request.method == "PUT" for request in seen)


def test_upsert_managed_task_verified_executes_then_verifies():
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "PUT" and path == "/api/workspace/ws/database/db/row":
            return json_response({"data": "managed-row", "code": 0})
        if request.method == "GET" and path == "/api/workspace/ws/database/db/row":
            return json_response({"data": [{"id": "managed-row"}]})
        if path == "/api/workspace/ws/database/db/row/detail":
            return json_response({"data": [{"id": "managed-row"}]})
        if path == "/api/workspace/v1/ws/collab/db/json":
            return json_response({"data": {"views": {"view_001": {"row_orders": ["managed-row"]}}}})
        if path == "/api/workspace/v1/ws/collab/managed-row/json":
            return json_response({"data": {"collab": {"database_row": {}}}})
        raise AssertionError(path)

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

    result = client.upsert_managed_task_verified(
        "ws",
        "db",
        task_key="task-1",
        description="Managed",
        dry_run=False,
        include_blob_diff=False,
    )

    assert result["upsert"]["data"] == "managed-row"
    assert result["verification"]["verified"] is True


def test_task_facing_methods_delegate_to_verified_managed_operations(monkeypatch):
    from appflowy_mcp_toolkit.client import AppFlowyClient

    client = AppFlowyClient(AppFlowyConfig(base_url="https://example.test", access_token="t"))
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_upsert(*_args: object, **kwargs: object) -> dict[str, object]:
        calls.append(("upsert", dict(kwargs)))
        return {"ok": True}

    def fake_move(*_args: object, **kwargs: object) -> dict[str, object]:
        calls.append(("move", dict(kwargs)))
        return {"ok": True}

    def fake_delete(*_args: object, **kwargs: object) -> dict[str, object]:
        calls.append(("delete", dict(kwargs)))
        return {"ok": True}

    monkeypatch.setattr(client, "upsert_managed_task_verified", fake_upsert)
    monkeypatch.setattr(client, "move_managed_task_status", fake_move)
    monkeypatch.setattr(client, "delete_database_row_collab", fake_delete)

    assert client.create_task("ws", "db", task_key="k", description="D") == {"ok": True}
    assert client.update_task("ws", "db", task_key="k", status="Doing") == {"ok": True}
    assert client.move_task("ws", "db", task_key="k", status="Done") == {"ok": True}
    assert client.delete_task("ws", "db", "row-1") == {"ok": True}

    assert calls[0] == (
        "upsert",
        {
            "task_key": "k",
            "description": "D",
            "status": "To Do",
            "document": None,
            "dry_run": True,
            "include_blob_diff": True,
        },
    )
    assert calls[1][0] == "upsert"
    assert calls[1][1]["status"] == "Doing"
    assert calls[2] == ("move", {"task_key": "k", "status": "Done", "dry_run": True})
    assert calls[3] == ("delete", {"dry_run": True})


def test_list_tasks_fetches_row_details(make_client):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/workspace/ws/database/db/row":
            return json_response({"data": [{"id": "row-1"}, {"id": "row-2"}]})
        if request.url.path == "/api/workspace/ws/database/db/row/detail":
            assert request.url.params["ids"] == "row-1,row-2"
            return json_response({"data": [{"id": "row-1"}, {"id": "row-2"}]})
        raise AssertionError(str(request.url))

    client = make_client(handler)

    result = client.list_tasks("ws", "db")

    assert result["row_ids"] == ["row-1", "row-2"]
    assert [row["id"] for row in result["rows"]] == ["row-1", "row-2"]


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
