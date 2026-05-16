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
    "appflowy_get_folder",
    "appflowy_list_databases",
    "appflowy_get_database_schema",
    "appflowy_list_database_row_ids",
    "appflowy_get_database_rows",
    "appflowy_list_select_options",
    "appflowy_get_collab_json",
    "appflowy_get_database_row_orders",
    "appflowy_get_database_blob_diff",
}

EXPECTED_WRITE_TOOLS = {
    "appflowy_create_database_row",
    "appflowy_upsert_database_row",
    "appflowy_upsert_managed_task",
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
