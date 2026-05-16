"""
Unit tests for row/card reordering and board column reordering.

All tests are offline: HTTP is mocked via httpx.MockTransport,
subprocess is mocked via monkeypatch. No cloud credentials needed.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any
from unittest.mock import patch

import httpx
import pytest

from appflowy_mcp_toolkit.collab.collab_delete import (
    invoke_yjs_reorder_column,
    invoke_yjs_reorder_row,
)
from appflowy_mcp_toolkit.config import AppFlowyConfig
from appflowy_mcp_toolkit.errors import AppFlowyError
from tests.helpers import json_response

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_DOC_STATE = list(range(8))
FAKE_DELTA = [10, 11, 12]

HELPER_REORDER_OK: dict[str, Any] = {
    "ok": True,
    "moved": True,
    "from_index": 2,
    "to_index": 0,
    "delta_update": FAKE_DELTA,
}

HELPER_REORDER_NOOP: dict[str, Any] = {
    "ok": True,
    "moved": False,
    "from_index": 1,
    "to_index": 1,
    "delta_update": [],
}


def _binary_collab_response(doc_state: list[int] | None = None) -> httpx.Response:
    return json_response(
        {
            "data": {
                "doc_state": doc_state if doc_state is not None else FAKE_DOC_STATE,
                "state_vector": [1, 2, 3],
                "version": 0,
                "object_id": "db-001",
            }
        }
    )


def _make_client(handler: Any, allow_writes: bool = False) -> Any:
    from appflowy_mcp_toolkit.client import AppFlowyClient

    config = AppFlowyConfig(
        base_url="https://example.test",
        access_token="test-token",
        allow_writes=allow_writes,
    )
    return AppFlowyClient(
        config,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


# ---------------------------------------------------------------------------
# invoke_yjs_reorder_row — mock subprocess
# ---------------------------------------------------------------------------


def test_invoke_yjs_reorder_row_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """invoke_yjs_reorder_row passes correct payload and returns parsed result."""

    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        sent = json.loads(kwargs["input"])
        assert sent["operation"] == "reorder_row"
        assert sent["view_id"] == "view-001"
        assert sent["row_id"] == "row-abc"
        assert sent["before_row_id"] == "row-xyz"
        assert sent["doc_state"] == FAKE_DOC_STATE
        return subprocess.CompletedProcess(
            args, returncode=0, stdout=json.dumps(HELPER_REORDER_OK), stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    with (
        patch("appflowy_mcp_toolkit.collab.collab_delete._require_node", return_value="node"),
        patch("appflowy_mcp_toolkit.collab.collab_delete._require_helper"),
    ):
        result = invoke_yjs_reorder_row(
            FAKE_DOC_STATE,
            view_id="view-001",
            row_id="row-abc",
            before_row_id="row-xyz",
        )
    assert result["ok"] is True
    assert result["moved"] is True
    assert result["from_index"] == 2
    assert result["to_index"] == 0


def test_invoke_yjs_reorder_row_append(monkeypatch: pytest.MonkeyPatch) -> None:
    """before_row_id=None is forwarded as null."""

    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        sent = json.loads(kwargs["input"])
        assert sent["before_row_id"] is None
        return subprocess.CompletedProcess(
            args, returncode=0, stdout=json.dumps(HELPER_REORDER_NOOP), stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    with (
        patch("appflowy_mcp_toolkit.collab.collab_delete._require_node", return_value="node"),
        patch("appflowy_mcp_toolkit.collab.collab_delete._require_helper"),
    ):
        result = invoke_yjs_reorder_row(
            FAKE_DOC_STATE,
            view_id="view-001",
            row_id="row-abc",
            before_row_id=None,
        )
    assert result["ok"] is True


# ---------------------------------------------------------------------------
# invoke_yjs_reorder_column — mock subprocess
# ---------------------------------------------------------------------------


def test_invoke_yjs_reorder_column_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """invoke_yjs_reorder_column passes correct payload and returns parsed result."""

    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        sent = json.loads(kwargs["input"])
        assert sent["operation"] == "reorder_column"
        assert sent["view_id"] == "view-board-1"
        assert sent["field_id"] == "field-status"
        assert sent["group_id"] == "opt-done"
        assert sent["before_group_id"] == "opt-todo"
        return subprocess.CompletedProcess(
            args, returncode=0, stdout=json.dumps(HELPER_REORDER_OK), stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    with (
        patch("appflowy_mcp_toolkit.collab.collab_delete._require_node", return_value="node"),
        patch("appflowy_mcp_toolkit.collab.collab_delete._require_helper"),
    ):
        result = invoke_yjs_reorder_column(
            FAKE_DOC_STATE,
            view_id="view-board-1",
            field_id="field-status",
            group_id="opt-done",
            before_group_id="opt-todo",
        )
    assert result["ok"] is True
    assert result["moved"] is True


def test_invoke_yjs_reorder_column_append(monkeypatch: pytest.MonkeyPatch) -> None:
    """before_group_id=None is forwarded as null."""

    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        sent = json.loads(kwargs["input"])
        assert sent["before_group_id"] is None
        return subprocess.CompletedProcess(
            args, returncode=0, stdout=json.dumps(HELPER_REORDER_NOOP), stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    with (
        patch("appflowy_mcp_toolkit.collab.collab_delete._require_node", return_value="node"),
        patch("appflowy_mcp_toolkit.collab.collab_delete._require_helper"),
    ):
        result = invoke_yjs_reorder_column(
            FAKE_DOC_STATE,
            view_id="view-board-1",
            field_id="field-status",
            group_id="opt-inprogress",
            before_group_id=None,
        )
    assert result["ok"] is True


# ---------------------------------------------------------------------------
# client.reorder_database_row_collab — dry-run
# ---------------------------------------------------------------------------


def test_client_reorder_row_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dry-run reorder returns summary without posting."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert "collab" in str(request.url)
        return _binary_collab_response()

    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args, returncode=0, stdout=json.dumps(HELPER_REORDER_OK), stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    with (
        patch("appflowy_mcp_toolkit.collab.collab_delete._require_node", return_value="node"),
        patch("appflowy_mcp_toolkit.collab.collab_delete._require_helper"),
    ):
        client = _make_client(handler, allow_writes=False)
        result = client.reorder_database_row_collab(
            "ws-1", "db-1", "view-1", "row-abc", before_row_id="row-xyz", dry_run=True
        )
    assert result["dry_run"] is True
    assert result["moved"] is True
    assert result["server_status"] is None


def test_client_reorder_row_rejects_without_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Live reorder raises when APPFLOWY_ALLOW_WRITES is not set."""

    def handler(request: httpx.Request) -> httpx.Response:
        return _binary_collab_response()

    client = _make_client(handler, allow_writes=False)
    with pytest.raises(AppFlowyError, match="APPFLOWY_ALLOW_WRITES"):
        client.reorder_database_row_collab("ws-1", "db-1", "view-1", "row-abc", dry_run=False)


def test_client_reorder_row_rejects_without_collab_writes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live reorder raises when APPFLOWY_ALLOW_COLLAB_WRITES is not set."""

    def handler(request: httpx.Request) -> httpx.Response:
        return _binary_collab_response()

    monkeypatch.setenv("APPFLOWY_ALLOW_COLLAB_WRITES", "false")
    client = _make_client(handler, allow_writes=True)
    with pytest.raises(AppFlowyError, match="APPFLOWY_ALLOW_COLLAB_WRITES"):
        client.reorder_database_row_collab("ws-1", "db-1", "view-1", "row-abc", dry_run=False)


# ---------------------------------------------------------------------------
# client.reorder_database_column_collab — dry-run
# ---------------------------------------------------------------------------


def test_client_reorder_column_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dry-run column reorder returns summary without posting."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert "collab" in str(request.url)
        return _binary_collab_response()

    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args, returncode=0, stdout=json.dumps(HELPER_REORDER_OK), stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    with (
        patch("appflowy_mcp_toolkit.collab.collab_delete._require_node", return_value="node"),
        patch("appflowy_mcp_toolkit.collab.collab_delete._require_helper"),
    ):
        client = _make_client(handler, allow_writes=False)
        result = client.reorder_database_column_collab(
            "ws-1",
            "db-1",
            "view-board-1",
            "field-status",
            "opt-done",
            before_group_id="opt-todo",
            dry_run=True,
        )
    assert result["dry_run"] is True
    assert result["moved"] is True
    assert result["server_status"] is None


def test_client_reorder_column_rejects_without_writes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live column reorder raises when APPFLOWY_ALLOW_WRITES is not set."""

    def handler(request: httpx.Request) -> httpx.Response:
        return _binary_collab_response()

    client = _make_client(handler, allow_writes=False)
    with pytest.raises(AppFlowyError, match="APPFLOWY_ALLOW_WRITES"):
        client.reorder_database_column_collab(
            "ws-1", "db-1", "view-board-1", "field-status", "opt-done", dry_run=False
        )


# ---------------------------------------------------------------------------
# Yjs helper data-shape tests (no subprocess, pure Python data checks)
# ---------------------------------------------------------------------------


def test_reorder_row_payload_shape() -> None:
    """invoke_yjs_reorder_row builds the correct JSON shape."""
    captured: list[dict[str, Any]] = []

    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured.append(json.loads(kwargs["input"]))
        return subprocess.CompletedProcess(
            args, returncode=0, stdout=json.dumps(HELPER_REORDER_OK), stderr=""
        )

    with (
        patch("subprocess.run", side_effect=fake_run),
        patch("appflowy_mcp_toolkit.collab.collab_delete._require_node", return_value="node"),
        patch("appflowy_mcp_toolkit.collab.collab_delete._require_helper"),
    ):
        invoke_yjs_reorder_row(
            [1, 2, 3],
            view_id="v1",
            row_id="r1",
            before_row_id="r2",
        )

    payload = captured[0]
    assert payload["operation"] == "reorder_row"
    assert payload["view_id"] == "v1"
    assert payload["row_id"] == "r1"
    assert payload["before_row_id"] == "r2"
    assert payload["doc_state"] == [1, 2, 3]


def test_reorder_column_payload_shape() -> None:
    """invoke_yjs_reorder_column builds the correct JSON shape."""
    captured: list[dict[str, Any]] = []

    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured.append(json.loads(kwargs["input"]))
        return subprocess.CompletedProcess(
            args, returncode=0, stdout=json.dumps(HELPER_REORDER_OK), stderr=""
        )

    with (
        patch("subprocess.run", side_effect=fake_run),
        patch("appflowy_mcp_toolkit.collab.collab_delete._require_node", return_value="node"),
        patch("appflowy_mcp_toolkit.collab.collab_delete._require_helper"),
    ):
        invoke_yjs_reorder_column(
            [1, 2, 3],
            view_id="v1",
            field_id="f1",
            group_id="g1",
            before_group_id=None,
        )

    payload = captured[0]
    assert payload["operation"] == "reorder_column"
    assert payload["view_id"] == "v1"
    assert payload["field_id"] == "f1"
    assert payload["group_id"] == "g1"
    assert payload["before_group_id"] is None
