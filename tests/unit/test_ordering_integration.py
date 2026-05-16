"""
Real helper integration tests for row/card and board column reordering.

These tests build synthetic Yjs documents, serialise them to doc_state bytes,
and pipe each payload into the actual yjs_helper.js subprocess (no mocks).
They are offline; no network access or AppFlowy credentials are required.

Requires Node.js 18+ and the yjs package:
    cd src/appflowy_mcp_toolkit/collab && npm install
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Locate Node and the helper scripts; skip the whole module if unavailable.
# ---------------------------------------------------------------------------

_REPO = Path(__file__).parents[2]
_HELPER_JS = _REPO / "src" / "appflowy_mcp_toolkit" / "collab" / "yjs_helper.js"
_BUILDER_JS = _REPO / "scripts" / "_ordering_builder.js"
_YJS_MODULE = _REPO / "src" / "appflowy_mcp_toolkit" / "collab" / "node_modules" / "yjs"

_NODE_AVAILABLE = False
try:
    _node_result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
    _NODE_AVAILABLE = _node_result.returncode == 0
except (FileNotFoundError, subprocess.TimeoutExpired):
    pass

_YJS_AVAILABLE = _YJS_MODULE.exists()

pytestmark = pytest.mark.skipif(
    not (_NODE_AVAILABLE and _YJS_AVAILABLE),
    reason=(
        "Node.js 18+ and yjs npm package required "
        "(cd src/appflowy_mcp_toolkit/collab && npm install)"
    ),
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _node(cmd: str, *args: Any) -> Any:
    """Call the offline builder script with YJS_PATH set."""
    result = subprocess.run(
        ["node", str(_BUILDER_JS), cmd, json.dumps(list(args))],
        capture_output=True,
        text=True,
        timeout=10,
        env={"YJS_PATH": str(_YJS_MODULE), "PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == 0, f"builder failed: {result.stderr}"
    return json.loads(result.stdout)


def _invoke_helper(payload: dict[str, Any]) -> dict[str, Any]:
    result = subprocess.run(
        ["node", str(_HELPER_JS)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
    )
    return json.loads(result.stdout)


def _apply_delta(doc_state: list[int], delta: list[int]) -> list[int]:
    return _node("applyDelta", doc_state, delta)


# ---------------------------------------------------------------------------
# Row reorder integration tests
# ---------------------------------------------------------------------------


def test_reorder_row_append_to_end() -> None:
    """Move first row to end (before_row_id=null) — the exact failing case."""
    doc_state = _node("buildRowDoc", "v1", ["a", "b", "c"])
    result = _invoke_helper(
        {
            "operation": "reorder_row",
            "view_id": "v1",
            "row_id": "a",
            "before_row_id": None,
            "doc_state": doc_state,
        }
    )
    assert result["ok"] is True
    assert result["moved"] is True
    assert result["from_index"] == 0
    assert result["to_index"] == 2
    final = _apply_delta(doc_state, result["delta_update"])
    assert _node("getRowOrder", final, "v1") == ["b", "c", "a"]


def test_reorder_row_move_to_front() -> None:
    """Move last row to first position."""
    doc_state = _node("buildRowDoc", "v2", ["a", "b", "c"])
    result = _invoke_helper(
        {
            "operation": "reorder_row",
            "view_id": "v2",
            "row_id": "c",
            "before_row_id": "a",
            "doc_state": doc_state,
        }
    )
    assert result["ok"] is True
    assert result["moved"] is True
    final = _apply_delta(doc_state, result["delta_update"])
    assert _node("getRowOrder", final, "v2") == ["c", "a", "b"]


def test_reorder_row_move_middle() -> None:
    """Move middle row before last."""
    doc_state = _node("buildRowDoc", "v3", ["a", "b", "c"])
    result = _invoke_helper(
        {
            "operation": "reorder_row",
            "view_id": "v3",
            "row_id": "a",
            "before_row_id": "c",
            "doc_state": doc_state,
        }
    )
    assert result["ok"] is True
    final = _apply_delta(doc_state, result["delta_update"])
    assert _node("getRowOrder", final, "v3") == ["b", "a", "c"]


def test_reorder_row_noop() -> None:
    """Row is already at the target position — moved=False."""
    doc_state = _node("buildRowDoc", "v4", ["a", "b", "c"])
    result = _invoke_helper(
        {
            "operation": "reorder_row",
            "view_id": "v4",
            "row_id": "a",
            "before_row_id": "b",
            "doc_state": doc_state,
        }
    )
    assert result["ok"] is True
    assert result["moved"] is False


def test_reorder_row_missing_row_id() -> None:
    """row_id not in row_orders returns ok=False."""
    doc_state = _node("buildRowDoc", "v5", ["a", "b"])
    result = _invoke_helper(
        {
            "operation": "reorder_row",
            "view_id": "v5",
            "row_id": "MISSING",
            "before_row_id": None,
            "doc_state": doc_state,
        }
    )
    assert result["ok"] is False
    assert "MISSING" in result["error"]


def test_reorder_row_missing_before_row_id() -> None:
    """before_row_id not in row_orders returns ok=False."""
    doc_state = _node("buildRowDoc", "v6", ["a", "b"])
    result = _invoke_helper(
        {
            "operation": "reorder_row",
            "view_id": "v6",
            "row_id": "a",
            "before_row_id": "GHOST",
            "doc_state": doc_state,
        }
    )
    assert result["ok"] is False


def test_reorder_row_preserves_item_fields() -> None:
    """Moved row retains its height field after reorder (clone faithfulness)."""
    doc_state = _node("buildRowDoc", "v7", ["a", "b", "c"])
    result = _invoke_helper(
        {
            "operation": "reorder_row",
            "view_id": "v7",
            "row_id": "a",
            "before_row_id": None,
            "doc_state": doc_state,
        }
    )
    assert result["ok"] is True
    # 'a' must end up last; height=60 was set by buildRowDoc
    final = _apply_delta(doc_state, result["delta_update"])
    order = _node("getRowOrder", final, "v7")
    assert order[-1] == "a"


# ---------------------------------------------------------------------------
# Column reorder integration tests
# ---------------------------------------------------------------------------


def test_reorder_column_append_to_end() -> None:
    """Move first column to end."""
    doc_state = _node("buildColumnDoc", "b1", "f-status", ["todo", "in-progress", "done"])
    result = _invoke_helper(
        {
            "operation": "reorder_column",
            "view_id": "b1",
            "field_id": "f-status",
            "group_id": "todo",
            "before_group_id": None,
            "doc_state": doc_state,
        }
    )
    assert result["ok"] is True
    assert result["moved"] is True
    final = _apply_delta(doc_state, result["delta_update"])
    assert _node("getColumnOrder", final, "b1", "f-status") == [
        "in-progress",
        "done",
        "todo",
    ]


def test_reorder_column_move_to_front() -> None:
    """Move last column to front."""
    doc_state = _node("buildColumnDoc", "b2", "f-status", ["todo", "in-progress", "done"])
    result = _invoke_helper(
        {
            "operation": "reorder_column",
            "view_id": "b2",
            "field_id": "f-status",
            "group_id": "done",
            "before_group_id": "todo",
            "doc_state": doc_state,
        }
    )
    assert result["ok"] is True
    final = _apply_delta(doc_state, result["delta_update"])
    assert _node("getColumnOrder", final, "b2", "f-status") == [
        "done",
        "todo",
        "in-progress",
    ]


def test_reorder_column_noop() -> None:
    """Column already at target position — moved=False."""
    doc_state = _node("buildColumnDoc", "b3", "f-status", ["todo", "in-progress", "done"])
    result = _invoke_helper(
        {
            "operation": "reorder_column",
            "view_id": "b3",
            "field_id": "f-status",
            "group_id": "in-progress",
            "before_group_id": "done",
            "doc_state": doc_state,
        }
    )
    assert result["ok"] is True
    assert result["moved"] is False


def test_reorder_column_missing_group_id() -> None:
    """group_id not found returns ok=False."""
    doc_state = _node("buildColumnDoc", "b4", "f-status", ["todo", "done"])
    result = _invoke_helper(
        {
            "operation": "reorder_column",
            "view_id": "b4",
            "field_id": "f-status",
            "group_id": "MISSING",
            "before_group_id": None,
            "doc_state": doc_state,
        }
    )
    assert result["ok"] is False
