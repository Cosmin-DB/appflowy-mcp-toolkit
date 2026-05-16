"""
Tests for the experimental collab_delete module and delete_database_row_collab client method.
All tests are offline: HTTP is mocked via httpx.MockTransport,
subprocess is mocked via monkeypatch.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any
from unittest.mock import patch

import httpx
import pytest

from appflowy_mcp_toolkit.collab.collab_delete import (
    CollabHelperError,
    allow_collab_writes,
    check_collab_helper_setup,
    invoke_yjs_add_select_option,
    invoke_yjs_delete,
    invoke_yjs_rename_select_option,
    invoke_yjs_set_select_option_visibility,
)
from appflowy_mcp_toolkit.config import AppFlowyConfig
from appflowy_mcp_toolkit.errors import AppFlowyError
from tests.helpers import json_response

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FAKE_DOC_STATE = list(range(8))  # minimal non-empty byte list for mocking
FAKE_DELTA = [1, 2, 3, 4, 5]

HELPER_OK_RESULT: dict[str, Any] = {
    "ok": True,
    "row_found": True,
    "views_affected": ["view-001", "view-002"],
    "view_row_counts": {
        "view-001": {"before": 5, "after": 4},
        "view-002": {"before": 3, "after": 2},
    },
    "delta_update": FAKE_DELTA,
}

HELPER_NOT_FOUND_RESULT: dict[str, Any] = {
    "ok": True,
    "row_found": False,
    "views_affected": [],
    "view_row_counts": {"view-001": {"before": 5, "after": 5}},
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


def _make_client_with_handler(handler: Any, allow_writes: bool = False) -> Any:
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
# invoke_yjs_delete — mock subprocess
# ---------------------------------------------------------------------------


def test_invoke_yjs_delete_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """invoke_yjs_delete returns parsed helper output on success."""

    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        sent = json.loads(kwargs["input"])
        assert sent["row_id"] == "row-abc"
        assert sent["doc_state"] == FAKE_DOC_STATE
        return subprocess.CompletedProcess(
            args, returncode=0, stdout=json.dumps(HELPER_OK_RESULT), stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    # Also stub out the filesystem checks so they don't fail in CI
    with (
        patch("appflowy_mcp_toolkit.collab.collab_delete._require_node", return_value="node"),
        patch("appflowy_mcp_toolkit.collab.collab_delete._require_helper"),
    ):
        result = invoke_yjs_delete(FAKE_DOC_STATE, "row-abc")

    assert result["ok"] is True
    assert result["row_found"] is True
    assert result["views_affected"] == ["view-001", "view-002"]
    assert result["delta_update"] == FAKE_DELTA


def test_invoke_yjs_delete_row_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """invoke_yjs_delete returns ok=True with row_found=False when row absent."""

    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args, returncode=0, stdout=json.dumps(HELPER_NOT_FOUND_RESULT), stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    with (
        patch("appflowy_mcp_toolkit.collab.collab_delete._require_node", return_value="node"),
        patch("appflowy_mcp_toolkit.collab.collab_delete._require_helper"),
    ):
        result = invoke_yjs_delete(FAKE_DOC_STATE, "row-missing")

    assert result["ok"] is True
    assert result["row_found"] is False


def test_invoke_yjs_delete_helper_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """invoke_yjs_delete raises CollabHelperError when helper reports ok=False."""

    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args,
            returncode=1,
            stdout=json.dumps({"ok": False, "error": "data.database not found"}),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    with (
        patch("appflowy_mcp_toolkit.collab.collab_delete._require_node", return_value="node"),
        patch("appflowy_mcp_toolkit.collab.collab_delete._require_helper"),
        pytest.raises(CollabHelperError, match="data.database not found"),
    ):
        invoke_yjs_delete(FAKE_DOC_STATE, "row-x")


def test_invoke_yjs_rename_select_option_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        sent = json.loads(kwargs["input"])
        assert sent["operation"] == "rename_select_option"
        assert sent["field_id"] == "status"
        assert sent["field_type"] == 3
        assert sent["option_id"] == "todo"
        assert sent["new_name"] == "Next"
        return subprocess.CompletedProcess(
            args,
            returncode=0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "option_id": "todo",
                    "previous_name": "To Do",
                    "option": {"id": "todo", "name": "Next"},
                    "renamed": True,
                    "delta_update": FAKE_DELTA,
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    with (
        patch("appflowy_mcp_toolkit.collab.collab_delete._require_node", return_value="node"),
        patch("appflowy_mcp_toolkit.collab.collab_delete._require_helper"),
    ):
        result = invoke_yjs_rename_select_option(
            FAKE_DOC_STATE,
            field_id="status",
            field_type=3,
            option_id="todo",
            new_name="Next",
        )

    assert result["renamed"] is True
    assert result["option"]["name"] == "Next"


def test_invoke_yjs_set_select_option_visibility_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        sent = json.loads(kwargs["input"])
        assert sent["operation"] == "set_select_option_visibility"
        assert sent["field_id"] == "status"
        assert sent["field_type"] == 3
        assert sent["option_name"] == "Next"
        assert sent["visible"] is False
        assert sent["view_id"] == "board"
        return subprocess.CompletedProcess(
            args,
            returncode=0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "option": {"id": "todo", "name": "Next"},
                    "visible": False,
                    "affected_views": ["board"],
                    "visibility_by_view": {"board": {"before": True, "after": False}},
                    "delta_update": FAKE_DELTA,
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    with (
        patch("appflowy_mcp_toolkit.collab.collab_delete._require_node", return_value="node"),
        patch("appflowy_mcp_toolkit.collab.collab_delete._require_helper"),
    ):
        result = invoke_yjs_set_select_option_visibility(
            FAKE_DOC_STATE,
            field_id="status",
            field_type=3,
            option_name="Next",
            visible=False,
            view_id="board",
        )

    assert result["visible"] is False
    assert result["affected_views"] == ["board"]


def test_invoke_yjs_add_select_option_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        sent = json.loads(kwargs["input"])
        assert sent["operation"] == "add_select_option"
        assert sent["option_id"] == "next"
        assert sent["name"] == "Next"
        return subprocess.CompletedProcess(
            args,
            returncode=0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "option_added": True,
                    "option": {"id": "next", "name": "Next", "color": "Purple"},
                    "affected_views": ["board"],
                    "delta_update": FAKE_DELTA,
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    with (
        patch("appflowy_mcp_toolkit.collab.collab_delete._require_node", return_value="node"),
        patch("appflowy_mcp_toolkit.collab.collab_delete._require_helper"),
    ):
        result = invoke_yjs_add_select_option(
            FAKE_DOC_STATE,
            field_id="status",
            field_type=3,
            option_id="next",
            name="Next",
        )

    assert result["option_added"] is True


def test_invoke_yjs_delete_node_missing() -> None:
    """invoke_yjs_delete raises CollabHelperError when node is not on PATH."""
    with (
        patch("shutil.which", return_value=None),
        pytest.raises(CollabHelperError, match="Node.js is required"),
    ):
        invoke_yjs_delete(FAKE_DOC_STATE, "row-x")


def test_invoke_yjs_delete_helper_js_missing(tmp_path: Any) -> None:
    """invoke_yjs_delete raises CollabHelperError when yjs_helper.js is absent."""
    with (
        patch("appflowy_mcp_toolkit.collab.collab_delete._require_node", return_value="node"),
        patch(
            "appflowy_mcp_toolkit.collab.collab_delete._HELPER_JS",
            tmp_path / "nonexistent.js",
        ),
        pytest.raises(CollabHelperError, match="Yjs helper script not found"),
    ):
        invoke_yjs_delete(FAKE_DOC_STATE, "row-x")


def test_check_collab_helper_setup_reports_missing_runtime(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import appflowy_mcp_toolkit.collab.collab_delete as cd_mod

    helper_js = tmp_path / "yjs_helper.js"
    package_json = tmp_path / "package.json"
    helper_js.write_text("// helper\n")
    package_json.write_text("{}\n")

    monkeypatch.setattr("shutil.which", lambda _name: None)
    monkeypatch.setattr(cd_mod, "_HELPER_JS", helper_js)
    monkeypatch.setattr(cd_mod, "_HELPER_PACKAGE_JSON", package_json)
    monkeypatch.setattr(cd_mod, "_HELPER_NODE_MODULES", tmp_path / "node_modules" / "yjs")

    result = check_collab_helper_setup()

    assert result["ok"] is False
    assert result["checks"]["node"]["ok"] is False
    assert "Node.js was not found" in result["checks"]["node"]["message"]
    assert result["checks"]["npm"]["ok"] is False
    assert result["checks"]["helper_script"]["ok"] is True
    assert result["checks"]["helper_package"]["ok"] is True
    assert result["checks"]["yjs_dependency"]["ok"] is False
    assert "npm install" in result["checks"]["yjs_dependency"]["message"]


def test_check_collab_helper_setup_success(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import appflowy_mcp_toolkit.collab.collab_delete as cd_mod

    helper_js = tmp_path / "yjs_helper.js"
    package_json = tmp_path / "package.json"
    yjs_dir = tmp_path / "node_modules" / "yjs"
    helper_js.write_text("// helper\n")
    package_json.write_text("{}\n")
    yjs_dir.mkdir(parents=True)

    monkeypatch.setattr("shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(cd_mod, "_HELPER_JS", helper_js)
    monkeypatch.setattr(cd_mod, "_HELPER_PACKAGE_JSON", package_json)
    monkeypatch.setattr(cd_mod, "_HELPER_NODE_MODULES", yjs_dir)

    def fake_run(args: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        version = "v20.11.1" if args[0].endswith("node") else "10.8.0"
        return subprocess.CompletedProcess(args, returncode=0, stdout=f"{version}\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = check_collab_helper_setup()

    assert result["ok"] is True
    assert result["checks"]["node"]["version"] == "v20.11.1"
    assert result["checks"]["npm"]["version"] == "10.8.0"
    assert result["checks"]["yjs_dependency"]["ok"] is True


def test_invoke_yjs_delete_rejects_old_node() -> None:
    with (
        patch("shutil.which", return_value="/usr/bin/node"),
        patch(
            "appflowy_mcp_toolkit.collab.collab_delete._command_version",
            return_value="v16.20.0",
        ),
        pytest.raises(CollabHelperError, match="Node.js 18\+ is required"),
    ):
        invoke_yjs_delete(FAKE_DOC_STATE, "row-x")


# ---------------------------------------------------------------------------
# allow_collab_writes
# ---------------------------------------------------------------------------


def test_allow_collab_writes_false_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APPFLOWY_ALLOW_COLLAB_WRITES", raising=False)
    assert allow_collab_writes() is False


def test_allow_collab_writes_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPFLOWY_ALLOW_COLLAB_WRITES", "true")
    assert allow_collab_writes() is True


# ---------------------------------------------------------------------------
# delete_database_row_collab — dry-run (mock HTTP + mock subprocess)
# ---------------------------------------------------------------------------


def _setup_dry_run_client(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Return a client configured for dry-run tests with mocked HTTP and helper."""

    def handler(request: httpx.Request) -> httpx.Response:
        # Only the binary collab endpoint should be called in dry-run
        assert "/collab/" in request.url.path
        assert (
            request.url.path.endswith(("db-001", "db-001/web-update")) is False
            or "web-update" not in request.url.path
        )
        return _binary_collab_response()

    client = _make_client_with_handler(handler)

    def fake_invoke(doc_state: list[int], row_id: str) -> dict[str, Any]:
        assert doc_state == FAKE_DOC_STATE
        return HELPER_OK_RESULT

    monkeypatch.setattr(
        "appflowy_mcp_toolkit.client.invoke_yjs_delete",
        fake_invoke,
        raising=False,
    )
    # Patch at the import site inside client.py
    import appflowy_mcp_toolkit.collab.collab_delete as cd_mod

    monkeypatch.setattr(cd_mod, "invoke_yjs_delete", fake_invoke)

    return client


def test_delete_row_dry_run_returns_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dry-run returns summary dict without POSTing."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _binary_collab_response()

    client = _make_client_with_handler(handler)

    def fake_invoke(doc_state: list[int], row_id: str) -> dict[str, Any]:
        return HELPER_OK_RESULT

    import appflowy_mcp_toolkit.collab.collab_delete as cd_mod

    monkeypatch.setattr(cd_mod, "invoke_yjs_delete", fake_invoke)

    result = client.delete_database_row_collab("ws-001", "db-001", "row-target", dry_run=True)

    assert result["dry_run"] is True
    assert result["row_found"] is True
    assert result["views_affected"] == ["view-001", "view-002"]
    assert result["delta_update_bytes"] == len(FAKE_DELTA)
    # Must NOT have posted to web-update
    assert all("web-update" not in r.url.path for r in seen)


def test_delete_row_dry_run_row_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dry-run with row_found=False includes warning, no post."""

    def handler(_: httpx.Request) -> httpx.Response:
        return _binary_collab_response()

    client = _make_client_with_handler(handler)

    def fake_invoke(doc_state: list[int], row_id: str) -> dict[str, Any]:
        return HELPER_NOT_FOUND_RESULT

    import appflowy_mcp_toolkit.collab.collab_delete as cd_mod

    monkeypatch.setattr(cd_mod, "invoke_yjs_delete", fake_invoke)

    result = client.delete_database_row_collab("ws-001", "db-001", "row-ghost", dry_run=True)

    assert result["row_found"] is False
    assert "warning" in result


def test_delete_row_live_requires_allow_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Live mode raises AppFlowyError if APPFLOWY_ALLOW_WRITES is not set."""

    def handler(_: httpx.Request) -> httpx.Response:
        return _binary_collab_response()

    client = _make_client_with_handler(handler, allow_writes=False)

    with pytest.raises(AppFlowyError, match="Writes are disabled"):
        client.delete_database_row_collab("ws-001", "db-001", "row-x", dry_run=False)


def test_delete_row_live_requires_allow_collab_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Live mode raises AppFlowyError if APPFLOWY_ALLOW_COLLAB_WRITES is not set."""
    monkeypatch.delenv("APPFLOWY_ALLOW_COLLAB_WRITES", raising=False)

    def handler(_: httpx.Request) -> httpx.Response:
        return _binary_collab_response()

    client = _make_client_with_handler(handler, allow_writes=True)

    with pytest.raises(AppFlowyError, match="APPFLOWY_ALLOW_COLLAB_WRITES"):
        client.delete_database_row_collab("ws-001", "db-001", "row-x", dry_run=False)


def test_delete_row_live_posts_delta_and_verifies(monkeypatch: pytest.MonkeyPatch) -> None:
    """Live mode posts delta and reports both row-list and row-detail verification."""
    monkeypatch.setenv("APPFLOWY_ALLOW_COLLAB_WRITES", "true")

    requests_seen: list[httpx.Request] = []

    # Build collab JSON response without the deleted row
    collab_after = {
        "data": {
            "collab": {
                "database": {
                    "views": {"view-001": {"row_orders": [{"id": "row-other", "height": 60}]}}
                }
            }
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        requests_seen.append(request)
        if "web-update" in request.url.path:
            return json_response({"code": 0, "message": "ok"})
        if request.url.path.endswith("/json"):
            return httpx.Response(200, json=collab_after)
        if "detail" in request.url.path:
            return json_response({"data": [{"id": "row-target"}]})
        if "/row" in request.url.path and "detail" not in request.url.path:
            return json_response({"data": [{"id": "row-other"}]})
        # binary collab endpoint
        return _binary_collab_response()

    client = _make_client_with_handler(handler, allow_writes=True)

    def fake_invoke(doc_state: list[int], row_id: str) -> dict[str, Any]:
        return HELPER_OK_RESULT

    import appflowy_mcp_toolkit.collab.collab_delete as cd_mod

    monkeypatch.setattr(cd_mod, "invoke_yjs_delete", fake_invoke)

    result = client.delete_database_row_collab("ws-001", "db-001", "row-target", dry_run=False)

    assert result["dry_run"] is False
    assert result["row_found"] is True
    assert "server_status" in result
    assert "collab_verified" in result
    assert result["rest_row_list_verified"] is True
    assert result["rest_verified"] is True
    assert result["row_detail_still_resolvable"] is True
    # Verify that web-update was called
    assert any("web-update" in r.url.path for r in requests_seen)


def test_delete_row_helper_error_surfaces_as_appflowy_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CollabHelperError from helper is re-raised as AppFlowyError."""

    def handler(_: httpx.Request) -> httpx.Response:
        return _binary_collab_response()

    client = _make_client_with_handler(handler)

    import appflowy_mcp_toolkit.collab.collab_delete as cd_mod

    monkeypatch.setattr(
        cd_mod,
        "invoke_yjs_delete",
        lambda *_: (_ for _ in ()).throw(CollabHelperError("Node.js missing")),
    )

    with pytest.raises(AppFlowyError, match="Node.js missing"):
        client.delete_database_row_collab("ws-001", "db-001", "row-x", dry_run=True)
