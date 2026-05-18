"""Tests for MCP tool annotations and protocol-level error handling.

FastMCP behaviour (this version):
  When a tool function raises an exception, FastMCP wraps it as a
  ``ToolError`` at the tool boundary.  The ToolError is converted to
  ``isError=True`` in the actual MCP wire protocol by the transport layer,
  but ``mcp.call_tool()`` in tests raises the ``ToolError`` directly.

  This is the expected protocol-correct behaviour: errors are *not* propagated
  as raw Python exceptions to the MCP client; they become tool-execution errors
  in the protocol, not crashes.  Tests below verify that behaviour.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import patch

import pytest

from appflowy_mcp_toolkit.errors import AppFlowyAuthError, AppFlowyError, AppFlowyRateLimitError
from appflowy_mcp_toolkit.mcp.server import mcp

try:
    from mcp.server.fastmcp.exceptions import ToolError
except ImportError:  # pragma: no cover
    ToolError = Exception  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Annotation inspection helpers
# ---------------------------------------------------------------------------


def _tool(name: str) -> Any:
    tools = asyncio.run(mcp.list_tools())
    t = next((t for t in tools if t.name == name), None)
    assert t is not None, f"Tool {name!r} not registered"
    return t


def _ann(name: str) -> Any:
    return _tool(name).annotations


# ---------------------------------------------------------------------------
# Annotation tests: readOnlyHint preserved
# ---------------------------------------------------------------------------


def test_read_tools_have_readonly_true():
    for name in (
        "appflowy_health_check",
        "appflowy_list_workspaces",
        "appflowy_get_server_info",
        "appflowy_list_databases",
        "appflowy_list_tasks",
        "appflowy_search_tasks",
        "appflowy_verify_database_row",
    ):
        assert _ann(name).readOnlyHint is True, f"{name} should have readOnlyHint=True"


def test_write_tools_have_readonly_false():
    for name in (
        "appflowy_create_task",
        "appflowy_delete_task",
        "appflowy_delete_database_row",
        "appflowy_publish_page",
        "appflowy_unpublish_page",
        "appflowy_upload_file_blob_v1",
        "appflowy_delete_file_blob_v1",
    ):
        assert _ann(name).readOnlyHint is False, f"{name} should have readOnlyHint=False"


# ---------------------------------------------------------------------------
# Annotation tests: destructiveHint
# ---------------------------------------------------------------------------


def test_destructive_tools_have_hint():
    destructive = (
        "appflowy_delete_task",
        "appflowy_delete_task_by_name",
        "appflowy_delete_database_row",
        "appflowy_delete_quick_note",
        "appflowy_delete_file_blob_v1",
        "appflowy_trash_page_view",
        "appflowy_delete_trashed_page_view",
        "appflowy_delete_all_pages_from_trash",
        "appflowy_unpublish_page",
    )
    for name in destructive:
        assert _ann(name).destructiveHint is True, f"{name} should have destructiveHint=True"


def test_read_tools_not_destructive():
    for name in ("appflowy_health_check", "appflowy_list_workspaces", "appflowy_list_tasks"):
        assert _ann(name).destructiveHint is not True, f"{name} should not be destructive"


# ---------------------------------------------------------------------------
# Annotation tests: openWorldHint
# ---------------------------------------------------------------------------


def test_open_world_tools_have_hint():
    open_world = (
        "appflowy_publish_page",
        "appflowy_unpublish_page",
        "appflowy_upload_file_blob_v1",
        "appflowy_upload_file_as_media",
        "appflowy_duplicate_published_page",
        "appflowy_instantiate_template",
        "appflowy_create_task",
        "appflowy_create_space",
        "appflowy_create_page_view",
        "appflowy_create_quick_note",
    )
    for name in open_world:
        assert _ann(name).openWorldHint is True, f"{name} should have openWorldHint=True"


# ---------------------------------------------------------------------------
# Annotation tests: idempotentHint
# ---------------------------------------------------------------------------


def test_read_tools_are_idempotent():
    idempotent = (
        "appflowy_health_check",
        "appflowy_list_workspaces",
        "appflowy_get_server_info",
        "appflowy_list_tasks",
        "appflowy_search_tasks",
    )
    for name in idempotent:
        assert _ann(name).idempotentHint is True, f"{name} should have idempotentHint=True"


# ---------------------------------------------------------------------------
# Protocol-level error tests
#
# FastMCP wraps tool function exceptions as ToolError (not raw AppFlowyError).
# The transport later converts ToolError to isError=True in the MCP protocol.
# We verify ToolError (not raw AppFlowyError) propagates from mcp.call_tool().
# ---------------------------------------------------------------------------


def test_read_tool_appflowy_error_becomes_tool_error():
    """A read tool that raises AppFlowyError must surface as ToolError, not crash."""
    with patch("appflowy_mcp_toolkit.mcp.server.AppFlowyClient") as cls:
        cls.return_value.__enter__.return_value.health_check.side_effect = AppFlowyError(
            "connection refused"
        )
        with pytest.raises(ToolError) as exc_info:
            asyncio.run(mcp.call_tool("appflowy_health_check", {}))

    assert "connection refused" in str(exc_info.value)


def test_read_tool_auth_error_becomes_tool_error():
    """Auth errors on read tools also surface as ToolError."""
    with patch("appflowy_mcp_toolkit.mcp.server.AppFlowyClient") as cls:
        cls.return_value.__enter__.return_value.list_workspaces.side_effect = AppFlowyAuthError(
            "invalid token"
        )
        with pytest.raises(ToolError) as exc_info:
            asyncio.run(mcp.call_tool("appflowy_list_workspaces", {}))

    assert "invalid token" in str(exc_info.value)


def test_read_tool_rate_limit_error_becomes_tool_error():
    """Rate-limit failures must be clean tool errors, not server crashes."""
    with patch("appflowy_mcp_toolkit.mcp.server.AppFlowyClient") as cls:
        cls.return_value.__enter__.return_value.list_workspaces.side_effect = (
            AppFlowyRateLimitError("Rate limit exceeded: overall calls per minute")
        )
        with pytest.raises(ToolError) as exc_info:
            asyncio.run(mcp.call_tool("appflowy_list_workspaces", {}))

    assert "Rate limit exceeded" in str(exc_info.value)


def test_write_tool_appflowy_error_becomes_tool_error():
    """A dry-run write tool that raises AppFlowyError must surface as ToolError."""
    with patch("appflowy_mcp_toolkit.mcp.server.AppFlowyClient") as cls:
        cls.return_value.__enter__.return_value.create_task.side_effect = AppFlowyError(
            "workspace not found"
        )
        with pytest.raises(ToolError) as exc_info:
            asyncio.run(
                mcp.call_tool(
                    "appflowy_create_task",
                    {
                        "workspace_id": "ws-1",
                        "database_id": "db-1",
                        "task_key": "t1",
                        "description": "Test",
                    },
                )
            )

    assert "workspace not found" in str(exc_info.value)


def test_live_write_gate_error_becomes_tool_error(monkeypatch: pytest.MonkeyPatch):
    """Closed write gates should surface as tool errors with actionable text."""
    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", "tok")
    monkeypatch.delenv("APPFLOWY_ALLOW_WRITES", raising=False)
    monkeypatch.delenv("APPFLOWY_ALLOW_PUBLISH_WRITES", raising=False)
    monkeypatch.setenv("APPFLOWY_RATE_LIMIT_ENABLED", "false")

    with pytest.raises(ToolError) as exc_info:
        asyncio.run(
            mcp.call_tool(
                "appflowy_publish_page",
                {"workspace_id": "ws-1", "view_id": "view-1", "dry_run": False},
            )
        )

    message = str(exc_info.value)
    assert "APPFLOWY_ALLOW_WRITES" in message
    assert "Traceback" not in message


def test_local_file_read_gate_error_becomes_tool_error(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Closed local-file gate should surface as a clean MCP tool error."""
    test_file = tmp_path / "upload.txt"
    test_file.write_text("hello", encoding="utf-8")
    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", "tok")
    monkeypatch.setenv("APPFLOWY_ALLOW_WRITES", "true")
    monkeypatch.delenv("APPFLOWY_ALLOW_LOCAL_FILE_READS", raising=False)
    monkeypatch.delenv("APPFLOWY_ALLOWED_FILE_ROOTS", raising=False)
    monkeypatch.setenv("APPFLOWY_RATE_LIMIT_ENABLED", "false")

    with pytest.raises(ToolError) as exc_info:
        asyncio.run(
            mcp.call_tool(
                "appflowy_upload_file_as_media",
                {
                    "workspace_id": "ws-1",
                    "database_id": "db-1",
                    "file_path": str(test_file),
                    "dry_run": True,
                },
            )
        )

    message = str(exc_info.value)
    assert "APPFLOWY_ALLOW_LOCAL_FILE_READS" in message
    assert "Traceback" not in message


def test_destructive_tool_error_becomes_tool_error():
    """delete_task raising AppFlowyError must surface as ToolError."""
    with patch("appflowy_mcp_toolkit.mcp.server.AppFlowyClient") as cls:
        cls.return_value.__enter__.return_value.delete_task.side_effect = AppFlowyError(
            "row not found"
        )
        with pytest.raises(ToolError) as exc_info:
            asyncio.run(
                mcp.call_tool(
                    "appflowy_delete_task",
                    {"workspace_id": "ws-1", "database_id": "db-1", "row_id": "r-1"},
                )
            )

    assert "row not found" in str(exc_info.value)


def test_tool_error_not_raw_appflowy_error():
    """Verify ToolError is raised, not the raw AppFlowyError itself (protocol boundary)."""
    with patch("appflowy_mcp_toolkit.mcp.server.AppFlowyClient") as cls:
        cls.return_value.__enter__.return_value.health_check.side_effect = AppFlowyError(
            "test error"
        )
        try:
            asyncio.run(mcp.call_tool("appflowy_health_check", {}))
            pytest.fail("Expected an exception")
        except ToolError:
            pass  # correct: wrapped as ToolError
        except AppFlowyError:
            pytest.fail(
                "Raw AppFlowyError leaked past tool boundary — FastMCP should wrap it as ToolError"
            )
