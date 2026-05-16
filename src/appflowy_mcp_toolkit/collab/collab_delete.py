"""
Experimental Yjs-based collab mutation helpers for AppFlowy database rows.

This module is experimental (M6.3). It requires Node.js 18+ and the ``yjs``
npm package installed alongside the helper script in
``src/appflowy_mcp_toolkit/collab/``.

Safety gates (both required for live writes):
  - ``APPFLOWY_ALLOW_WRITES=true``
  - ``APPFLOWY_ALLOW_COLLAB_WRITES=true``
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

_HELPER_JS = Path(__file__).parent / "yjs_helper.js"
_HELPER_PACKAGE_JSON = Path(__file__).parent / "package.json"
_HELPER_NODE_MODULES = Path(__file__).parent / "node_modules" / "yjs"
_MIN_NODE_MAJOR = 18


def _install_command() -> str:
    return f"cd {Path(__file__).parent} && npm install"


class CollabHelperError(RuntimeError):
    """Raised when the Yjs helper subprocess fails or is unavailable."""


def _parse_node_major(version_output: str) -> int | None:
    version = version_output.strip()
    if version.startswith("v"):
        version = version[1:]
    major, _, _ = version.partition(".")
    try:
        return int(major)
    except ValueError:
        return None


def _command_version(executable: str) -> str | None:
    try:
        proc = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return (proc.stdout or proc.stderr).strip() or None


def check_collab_helper_setup() -> dict[str, Any]:
    """Return local setup diagnostics for the Node/Yjs collab helper."""
    install_command = _install_command()
    checks: dict[str, dict[str, Any]] = {}

    node = shutil.which("node")
    node_version = _command_version(node) if node else None
    node_major = _parse_node_major(node_version or "") if node_version else None
    node_ok = bool(node and node_major is not None and node_major >= _MIN_NODE_MAJOR)
    node_message = "Node.js 18+ found."
    if node is None:
        node_message = "Node.js was not found on PATH. Install Node.js 18+."
    elif node_major is None:
        node_message = f"Could not parse Node.js version from {node_version!r}; require 18+."
    elif node_major < _MIN_NODE_MAJOR:
        node_message = f"Node.js {node_version} is too old; install Node.js 18+."
    checks["node"] = {
        "ok": node_ok,
        "path": node,
        "version": node_version,
        "message": node_message,
    }

    npm = shutil.which("npm")
    npm_version = _command_version(npm) if npm else None
    checks["npm"] = {
        "ok": npm is not None,
        "path": npm,
        "version": npm_version,
        "message": (
            "npm found."
            if npm is not None
            else "npm was not found on PATH. Install npm, then run the install command."
        ),
    }

    checks["helper_script"] = {
        "ok": _HELPER_JS.exists(),
        "path": str(_HELPER_JS),
        "message": (
            "Yjs helper script found."
            if _HELPER_JS.exists()
            else "Yjs helper script is missing; this is a packaging issue."
        ),
    }
    checks["helper_package"] = {
        "ok": _HELPER_PACKAGE_JSON.exists(),
        "path": str(_HELPER_PACKAGE_JSON),
        "message": (
            "Helper package.json found."
            if _HELPER_PACKAGE_JSON.exists()
            else "Helper package.json is missing; this is a packaging issue."
        ),
    }
    checks["yjs_dependency"] = {
        "ok": _HELPER_NODE_MODULES.exists(),
        "path": str(_HELPER_NODE_MODULES),
        "message": (
            "yjs dependency installed."
            if _HELPER_NODE_MODULES.exists()
            else f"yjs dependency is not installed. Run: {install_command}"
        ),
    }

    ok = all(check["ok"] for check in checks.values())
    return {
        "ok": ok,
        "helper_dir": str(Path(__file__).parent),
        "install_command": install_command,
        "checks": checks,
    }


def _require_node() -> str:
    """Return the path to node, or raise CollabHelperError if not found."""
    node = shutil.which("node")
    if node is None:
        raise CollabHelperError(
            "Node.js is required for collab mutations but was not found on PATH. "
            f"Install Node.js 18+ and run: {_install_command()}"
        )
    version = _command_version(node)
    major = _parse_node_major(version or "") if version else None
    if major is None or major < _MIN_NODE_MAJOR:
        raise CollabHelperError(
            f"Node.js 18+ is required for collab mutations; found {version or 'unknown'}. "
            "Install Node.js 18+."
        )
    return node


def _require_helper() -> None:
    """Raise CollabHelperError if the JS helper or yjs module is missing."""
    if not _HELPER_JS.exists():
        raise CollabHelperError(
            f"Yjs helper script not found: {_HELPER_JS}. "
            "This is a packaging issue; ensure yjs_helper.js is present."
        )
    if not _HELPER_NODE_MODULES.exists():
        raise CollabHelperError(
            f"yjs npm package not found at {_HELPER_NODE_MODULES}. Run: {_install_command()}"
        )


def _invoke_yjs_helper(payload: dict[str, Any]) -> dict[str, Any]:
    node = _require_node()
    _require_helper()

    try:
        proc = subprocess.run(
            [node, str(_HELPER_JS)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise CollabHelperError("Yjs helper timed out after 30 seconds") from exc
    except OSError as exc:
        raise CollabHelperError(f"Failed to run Yjs helper: {exc}") from exc

    if proc.returncode not in (0, 1):
        raise CollabHelperError(
            f"Yjs helper exited with code {proc.returncode}. stderr: {proc.stderr.strip()[:200]}"
        )

    try:
        result: dict[str, Any] = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise CollabHelperError(
            f"Yjs helper returned non-JSON output: {proc.stdout[:200]!r}"
        ) from exc

    if not result.get("ok"):
        raise CollabHelperError(f"Yjs helper error: {result.get('error', 'unknown')}")

    return result


def invoke_yjs_delete(doc_state: list[int], row_id: str) -> dict[str, Any]:
    """Call the Yjs helper to compute a row-delete delta from binary collab state.

    Parameters
    ----------
    doc_state:
        Raw lib0-v1 bytes from AppFlowy Cloud binary collab endpoint, as a
        list of ints (the JSON array format returned by the API).
    row_id:
        UUID string of the row to delete from all views' ``row_orders``.

    Returns
    -------
    dict with keys:
      - ``ok`` (bool)
      - ``row_found`` (bool)
      - ``views_affected`` (list[str])
      - ``view_row_counts`` (dict[str, dict[str, int]])
      - ``delta_update`` (list[int])

    Raises
    ------
    CollabHelperError
        If Node.js is missing, the helper is missing, or the subprocess fails.
    """
    return _invoke_yjs_helper({"operation": "delete_row", "doc_state": doc_state, "row_id": row_id})


def invoke_yjs_update_row_cells(
    doc_state: list[int], cell_updates: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Call the Yjs helper to compute a DatabaseRow cell-update delta.

    cell_updates must be keyed by AppFlowy field id. Each value contains
    the integer field_type and the already-normalized internal data.
    """
    return _invoke_yjs_helper(
        {
            "operation": "update_row_cells",
            "doc_state": doc_state,
            "cells": cell_updates,
        }
    )


def invoke_yjs_add_select_option(
    doc_state: list[int],
    *,
    field_id: str,
    field_type: int,
    option_id: str,
    name: str,
    color: str = "Purple",
    view_id: str | None = None,
) -> dict[str, Any]:
    """Call the Yjs helper to add a select option to a database field.

    Board columns are stored as options of the grouped select field, plus a
    visible group entry in board views. This helper updates both in one Database
    collab delta.
    """
    payload: dict[str, Any] = {
        "operation": "add_select_option",
        "doc_state": doc_state,
        "field_id": field_id,
        "field_type": field_type,
        "option_id": option_id,
        "name": name,
        "color": color,
    }
    if view_id is not None:
        payload["view_id"] = view_id
    return _invoke_yjs_helper(payload)


def invoke_yjs_rename_select_option(
    doc_state: list[int],
    *,
    field_id: str,
    field_type: int,
    new_name: str,
    option_id: str | None = None,
    option_name: str | None = None,
) -> dict[str, Any]:
    """Call the Yjs helper to rename a select option in a database field."""
    payload: dict[str, Any] = {
        "operation": "rename_select_option",
        "doc_state": doc_state,
        "field_id": field_id,
        "field_type": field_type,
        "new_name": new_name,
    }
    if option_id is not None:
        payload["option_id"] = option_id
    if option_name is not None:
        payload["option_name"] = option_name
    return _invoke_yjs_helper(payload)


def invoke_yjs_set_select_option_visibility(
    doc_state: list[int],
    *,
    field_id: str,
    field_type: int,
    visible: bool,
    option_id: str | None = None,
    option_name: str | None = None,
    view_id: str | None = None,
) -> dict[str, Any]:
    """Call the Yjs helper to show/hide a select option in board view groups."""
    payload: dict[str, Any] = {
        "operation": "set_select_option_visibility",
        "doc_state": doc_state,
        "field_id": field_id,
        "field_type": field_type,
        "visible": visible,
    }
    if option_id is not None:
        payload["option_id"] = option_id
    if option_name is not None:
        payload["option_name"] = option_name
    if view_id is not None:
        payload["view_id"] = view_id
    return _invoke_yjs_helper(payload)


def invoke_yjs_reorder_row(
    doc_state: list[int],
    *,
    view_id: str,
    row_id: str,
    before_row_id: str | None,
) -> dict[str, Any]:
    """Call the Yjs helper to reorder a row inside a database view's row_orders.

    ``before_row_id=None`` moves the row to the end of the view.
    """
    payload: dict[str, Any] = {
        "operation": "reorder_row",
        "doc_state": doc_state,
        "view_id": view_id,
        "row_id": row_id,
        "before_row_id": before_row_id,
    }
    return _invoke_yjs_helper(payload)


def invoke_yjs_reorder_column(
    doc_state: list[int],
    *,
    view_id: str,
    field_id: str,
    group_id: str,
    before_group_id: str | None,
) -> dict[str, Any]:
    """Call the Yjs helper to reorder a board column inside a database view.

    ``before_group_id=None`` moves the column to the end.
    """
    payload: dict[str, Any] = {
        "operation": "reorder_column",
        "doc_state": doc_state,
        "view_id": view_id,
        "field_id": field_id,
        "group_id": group_id,
        "before_group_id": before_group_id,
    }
    return _invoke_yjs_helper(payload)


def allow_collab_writes() -> bool:
    """Return True if APPFLOWY_ALLOW_COLLAB_WRITES is set to a truthy value."""
    return os.getenv("APPFLOWY_ALLOW_COLLAB_WRITES", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
