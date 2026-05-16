from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import patch

from appflowy_mcp_toolkit.mcp.server import mcp

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EXPECTED_READ_TOOLS = {
    "appflowy_health_check",
    "appflowy_list_workspaces",
    "appflowy_get_workspace_settings",
    "appflowy_list_workspace_members",
    "appflowy_get_workspace_usage",
    "appflowy_list_recent_views",
    "appflowy_list_favorite_views",
    "appflowy_list_trash_views",
    "appflowy_get_folder",
    "appflowy_list_databases",
    "appflowy_get_database_schema",
    "appflowy_list_database_row_ids",
    "appflowy_list_updated_database_rows",
    "appflowy_get_database_rows",
    "appflowy_search_documents",
    "appflowy_list_select_options",
    "appflowy_get_collab_json",
    "appflowy_get_database_row_orders",
    "appflowy_get_database_blob_diff",
    "appflowy_list_tasks",
    "appflowy_verify_database_row",
}

EXPECTED_WRITE_TOOLS = {
    "appflowy_create_task",
    "appflowy_update_task",
    "appflowy_move_task",
    "appflowy_delete_task",
    "appflowy_create_database_row",
    "appflowy_create_verified_database_row",
    "appflowy_upsert_database_row",
    "appflowy_upsert_managed_task",
    "appflowy_upsert_verified_managed_task",
    "appflowy_move_managed_task_status",
    "appflowy_delete_database_row",
}

EXPECTED_ALL_TOOLS = EXPECTED_READ_TOOLS | EXPECTED_WRITE_TOOLS


def _get_tools() -> list[Any]:
    return asyncio.run(mcp.list_tools())


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


def test_all_expected_tools_are_registered() -> None:
    tools = _get_tools()
    names = {t.name for t in tools}
    assert names == EXPECTED_ALL_TOOLS, (
        f"Missing: {EXPECTED_ALL_TOOLS - names}  Extra: {names - EXPECTED_ALL_TOOLS}"
    )


def test_read_tools_have_readonly_hint_true() -> None:
    tools = _get_tools()
    for tool in tools:
        if tool.name in EXPECTED_READ_TOOLS:
            assert tool.annotations.readOnlyHint is True, (
                f"{tool.name} should have readOnlyHint=True"
            )


def test_write_tools_have_readonly_hint_false() -> None:
    tools = _get_tools()
    for tool in tools:
        if tool.name in EXPECTED_WRITE_TOOLS:
            assert tool.annotations.readOnlyHint is False, (
                f"{tool.name} should have readOnlyHint=False"
            )


# ---------------------------------------------------------------------------
# Health check smoke via FastMCP.call_tool (no real network)
# ---------------------------------------------------------------------------


def test_health_check_tool_returns_ok_json() -> None:
    """Call appflowy_health_check through FastMCP without real network or secrets."""
    fake_result = {"ok": True, "base_url": "https://example.test"}

    with patch(
        "appflowy_mcp_toolkit.mcp.server.AppFlowyClient",
        autospec=True,
    ) as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.health_check.return_value = fake_result

        raw: Any = asyncio.run(mcp.call_tool("appflowy_health_check", {}))

    content_blocks = raw[0]
    assert len(content_blocks) == 1
    parsed = json.loads(content_blocks[0].text)
    assert parsed == fake_result


def test_updated_rows_tool_delegates_to_client() -> None:
    fake_result = [{"id": "row-1"}]

    with patch(
        "appflowy_mcp_toolkit.mcp.server.AppFlowyClient",
        autospec=True,
    ) as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.list_updated_database_rows.return_value = fake_result

        raw: Any = asyncio.run(
            mcp.call_tool(
                "appflowy_list_updated_database_rows",
                {
                    "workspace_id": "ws",
                    "database_id": "db",
                    "after": "2026-05-16T10:00:00Z",
                },
            )
        )

    instance.list_updated_database_rows.assert_called_once_with(
        "ws",
        "db",
        after="2026-05-16T10:00:00Z",
    )
    content_blocks = raw[0]
    assert json.loads(content_blocks[0].text) == fake_result


def test_search_documents_tool_delegates_to_client() -> None:
    fake_result = [{"object_id": "page-1", "preview": "roadmap"}]

    with patch(
        "appflowy_mcp_toolkit.mcp.server.AppFlowyClient",
        autospec=True,
    ) as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.search_documents.return_value = fake_result

        raw: Any = asyncio.run(
            mcp.call_tool(
                "appflowy_search_documents",
                {
                    "workspace_id": "ws",
                    "query": "roadmap",
                    "limit": 5,
                    "preview_size": 120,
                    "score": 0.4,
                },
            )
        )

    instance.search_documents.assert_called_once_with(
        "ws",
        "roadmap",
        limit=5,
        preview_size=120,
        score=0.4,
    )
    content_blocks = raw[0]
    assert json.loads(content_blocks[0].text) == fake_result


def test_workspace_readonly_tools_delegate_to_client() -> None:
    with patch(
        "appflowy_mcp_toolkit.mcp.server.AppFlowyClient",
        autospec=True,
    ) as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.get_workspace_settings.return_value = {"workspace_id": "ws", "name": "Demo"}
        instance.list_workspace_members.return_value = [{"email": "demo@example.test"}]
        instance.get_workspace_usage.return_value = {"storage_bytes": 2048}

        settings_raw: Any = asyncio.run(
            mcp.call_tool("appflowy_get_workspace_settings", {"workspace_id": "ws"})
        )
        members_raw: Any = asyncio.run(
            mcp.call_tool("appflowy_list_workspace_members", {"workspace_id": "ws"})
        )
        usage_raw: Any = asyncio.run(
            mcp.call_tool("appflowy_get_workspace_usage", {"workspace_id": "ws"})
        )

    instance.get_workspace_settings.assert_called_once_with("ws")
    instance.list_workspace_members.assert_called_once_with("ws")
    instance.get_workspace_usage.assert_called_once_with("ws")
    assert json.loads(settings_raw[0][0].text) == {"workspace_id": "ws", "name": "Demo"}
    assert json.loads(members_raw[0][0].text) == [{"email": "demo@example.test"}]
    assert json.loads(usage_raw[0][0].text) == {"storage_bytes": 2048}


def test_navigation_readonly_tools_delegate_to_client() -> None:
    with patch(
        "appflowy_mcp_toolkit.mcp.server.AppFlowyClient",
        autospec=True,
    ) as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.list_recent_views.return_value = [{"view_id": "recent"}]
        instance.list_favorite_views.return_value = [{"view_id": "favorite"}]
        instance.list_trash_views.return_value = [{"view_id": "trash"}]

        recent_raw: Any = asyncio.run(
            mcp.call_tool("appflowy_list_recent_views", {"workspace_id": "ws"})
        )
        favorites_raw: Any = asyncio.run(
            mcp.call_tool("appflowy_list_favorite_views", {"workspace_id": "ws"})
        )
        trash_raw: Any = asyncio.run(
            mcp.call_tool("appflowy_list_trash_views", {"workspace_id": "ws"})
        )

    instance.list_recent_views.assert_called_once_with("ws")
    instance.list_favorite_views.assert_called_once_with("ws")
    instance.list_trash_views.assert_called_once_with("ws")
    assert json.loads(recent_raw[0][0].text) == [{"view_id": "recent"}]
    assert json.loads(favorites_raw[0][0].text) == [{"view_id": "favorite"}]
    assert json.loads(trash_raw[0][0].text) == [{"view_id": "trash"}]
