"""Tests for get_collab_json safer defaults and summary mode."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import patch

import httpx

from appflowy_mcp_toolkit.cli.main import main
from appflowy_mcp_toolkit.config import AppFlowyConfig
from appflowy_mcp_toolkit.mcp.server import mcp

_FAKE_COLLAB = {
    "collab": {
        "database": {
            "views": {"view_001": {"row_orders": [{"id": "r1"}]}},
            "fields": [{"id": "f1", "name": "Description"}],
        }
    },
    "internal_state": "LARGE_YJS_BLOB_PLACEHOLDER",
}


def _make_client(handler):
    from appflowy_mcp_toolkit.client import AppFlowyClient

    cfg = AppFlowyConfig(base_url="https://example.test", access_token="tok")
    return AppFlowyClient(cfg, http_client=httpx.Client(transport=httpx.MockTransport(handler)))


def _handler(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"data": _FAKE_COLLAB})


# ---------------------------------------------------------------------------
# Client: summary_only=True (default for public callers)
# ---------------------------------------------------------------------------


def test_summary_default_returns_summary_not_raw():
    with _make_client(_handler) as client:
        result = client.get_collab_json("ws-1", "obj-1")
    assert result["diagnostic"] is True
    assert "raw" not in result
    # The raw value (the LARGE_YJS_BLOB_PLACEHOLDER string) must not be present
    assert "LARGE_YJS_BLOB_PLACEHOLDER" not in str(result)
    assert "top_level_keys" in result


def test_summary_includes_key_counts():
    with _make_client(_handler) as client:
        result = client.get_collab_json("ws-1", "obj-1", summary_only=True, include_raw=False)
    assert result["top_level_key_count"] == len(_FAKE_COLLAB)
    assert set(result["top_level_keys"]) == set(_FAKE_COLLAB.keys())


def test_summary_metadata_fields():
    with _make_client(_handler) as client:
        result = client.get_collab_json(
            "ws-1", "obj-1", collab_type="Database", summary_only=True, include_raw=False
        )
    assert result["workspace_id"] == "ws-1"
    assert result["object_id"] == "obj-1"
    assert result["collab_type"] == "Database"
    assert "raw_risk_note" in result


# ---------------------------------------------------------------------------
# Client: include_raw=True
# ---------------------------------------------------------------------------


def test_include_raw_true_returns_raw_in_result():
    with _make_client(_handler) as client:
        result = client.get_collab_json("ws-1", "obj-1", summary_only=True, include_raw=True)
    assert "raw" in result
    assert result["raw"] == _FAKE_COLLAB


def test_include_raw_false_no_raw_field():
    with _make_client(_handler) as client:
        result = client.get_collab_json("ws-1", "obj-1", summary_only=True, include_raw=False)
    assert "raw" not in result


# ---------------------------------------------------------------------------
# Client: summary_only=False (full raw — internal/backward compat path)
# ---------------------------------------------------------------------------


def test_summary_only_false_returns_full_raw():
    with _make_client(_handler) as client:
        result = client.get_collab_json("ws-1", "obj-1", summary_only=False, include_raw=True)
    assert result == _FAKE_COLLAB


def test_internal_callers_unchanged():
    """get_database_row_orders uses get_collab_json internally and must still work."""
    fake_db_collab = {
        "collab": {
            "database": {
                "views": {"view_001": {"row_orders": [{"id": "row_aaa"}, {"id": "row_bbb"}]}}
            }
        }
    }

    def handler(_r: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": fake_db_collab})

    with _make_client(handler) as client:
        orders = client.get_database_row_orders("ws-1", "db-1")

    assert len(orders) == 1
    assert orders[0]["row_orders"] == ["row_aaa", "row_bbb"]


# ---------------------------------------------------------------------------
# CLI: default is summary
# ---------------------------------------------------------------------------


def _patch_cli(monkeypatch):
    import httpx as _httpx

    from appflowy_mcp_toolkit import client as cm

    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", "tok")
    _real = _httpx.Client

    def fake(*a, **kw):
        return _real(transport=_httpx.MockTransport(_handler))

    monkeypatch.setattr(cm.httpx, "Client", fake)


def test_cli_collab_json_default_is_summary(monkeypatch, capsys):
    _patch_cli(monkeypatch)
    rc = main(["collab-json", "--workspace-id", "ws-1", "--object-id", "obj-1"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["diagnostic"] is True
    assert "raw" not in out


def test_cli_collab_json_include_raw_flag(monkeypatch, capsys):
    _patch_cli(monkeypatch)
    rc = main(
        [
            "collab-json",
            "--workspace-id",
            "ws-1",
            "--object-id",
            "obj-1",
            "--include-raw",
        ]
    )
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["diagnostic"] is True
    assert "raw" in out


def test_cli_collab_json_full_flag(monkeypatch, capsys):
    _patch_cli(monkeypatch)
    rc = main(
        [
            "collab-json",
            "--workspace-id",
            "ws-1",
            "--object-id",
            "obj-1",
            "--full",
        ]
    )
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    # --full bypasses summary: should return raw collab directly
    assert "diagnostic" not in out
    assert out == _FAKE_COLLAB


# ---------------------------------------------------------------------------
# MCP: default is summary
# ---------------------------------------------------------------------------


def test_mcp_get_collab_json_default_is_summary():
    with patch("appflowy_mcp_toolkit.mcp.server.AppFlowyClient") as cls:
        instance = cls.return_value.__enter__.return_value
        instance.get_collab_json.return_value = {
            "diagnostic": True,
            "workspace_id": "ws-1",
            "object_id": "obj-1",
            "collab_type": "Database",
            "top_level_keys": ["collab"],
            "top_level_key_count": 1,
            "raw_risk_note": "...",
        }
        raw: Any = asyncio.run(
            mcp.call_tool(
                "appflowy_get_collab_json",
                {"workspace_id": "ws-1", "object_id": "obj-1"},
            )
        )
    instance.get_collab_json.assert_called_once_with(
        "ws-1",
        "obj-1",
        collab_type="Database",
        summary_only=True,
        include_raw=False,
    )
    result = json.loads(raw[0][0].text)
    assert result["diagnostic"] is True


def test_mcp_get_collab_json_registered():
    tools = asyncio.run(mcp.list_tools())
    tool = next((t for t in tools if t.name == "appflowy_get_collab_json"), None)
    assert tool is not None
    assert getattr(tool.annotations, "readOnlyHint", False) is True
    desc = tool.description or ""
    assert "diagnostic" in desc.lower() or "raw" in desc.lower()
