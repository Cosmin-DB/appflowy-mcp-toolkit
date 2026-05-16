"""
Experimental Yjs-based collab delete helper for AppFlowy database rows.

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
_HELPER_NODE_MODULES = Path(__file__).parent / "node_modules" / "yjs"


class CollabHelperError(RuntimeError):
    """Raised when the Yjs helper subprocess fails or is unavailable."""


def _require_node() -> str:
    """Return the path to node, or raise CollabHelperError if not found."""
    node = shutil.which("node")
    if node is None:
        raise CollabHelperError(
            "Node.js is required for collab mutations but was not found on PATH. "
            "Install Node.js 18+ and run: "
            "cd src/appflowy_mcp_toolkit/collab && npm install"
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
            f"yjs npm package not found at {_HELPER_NODE_MODULES}. "
            "Run: cd src/appflowy_mcp_toolkit/collab && npm install"
        )


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
    node = _require_node()
    _require_helper()

    payload = json.dumps({"doc_state": doc_state, "row_id": row_id})
    try:
        proc = subprocess.run(
            [node, str(_HELPER_JS)],
            input=payload,
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


def allow_collab_writes() -> bool:
    """Return True if APPFLOWY_ALLOW_COLLAB_WRITES is set to a truthy value."""
    return os.getenv("APPFLOWY_ALLOW_COLLAB_WRITES", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
