"""Unit tests for publish/unpublish page write operations.

Routes confirmed in AppFlowy-Cloud src/api/workspace.rs:
  POST /api/workspace/{workspace_id}/page-view/{view_id}/publish
  POST /api/workspace/{workspace_id}/page-view/{view_id}/unpublish

Tests cover:
- dry-run shape (no network call)
- live gate: APPFLOWY_ALLOW_WRITES alone is not enough
- live gate: APPFLOWY_ALLOW_PUBLISH_WRITES alone is not enough
- live execution: both gates enabled → correct URL/payload
- CLI dispatch (publish-page, unpublish-page)
- MCP tool delegation
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import patch

import httpx
import pytest

from appflowy_mcp_toolkit.cli.main import main
from appflowy_mcp_toolkit.errors import AppFlowyError
from appflowy_mcp_toolkit.mcp.server import mcp

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(monkeypatch, *, allow_writes: bool, allow_publish: bool, handler=None):
    """Return an AppFlowyClient configured with the given gates."""
    import httpx as _httpx

    from appflowy_mcp_toolkit import client as client_module

    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("APPFLOWY_ALLOW_WRITES", "true" if allow_writes else "false")
    monkeypatch.setenv("APPFLOWY_ALLOW_PUBLISH_WRITES", "true" if allow_publish else "false")

    if handler is not None:
        _real = _httpx.Client

        def fake_client(*a, **kw):
            return _real(transport=_httpx.MockTransport(handler))

        monkeypatch.setattr(client_module.httpx, "Client", fake_client)

    from appflowy_mcp_toolkit.client import AppFlowyClient

    return AppFlowyClient()


def _patch_cli(monkeypatch, handler, *, allow_writes=True, allow_publish=True):
    """Patch httpx for CLI tests."""
    import httpx as _httpx

    from appflowy_mcp_toolkit import client as client_module

    _real = _httpx.Client

    def fake_client(*a, **kw):
        return _real(transport=_httpx.MockTransport(handler))

    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("APPFLOWY_ALLOW_WRITES", "true" if allow_writes else "false")
    monkeypatch.setenv("APPFLOWY_ALLOW_PUBLISH_WRITES", "true" if allow_publish else "false")
    monkeypatch.setattr(client_module.httpx, "Client", fake_client)


# ---------------------------------------------------------------------------
# Client: dry-run
# ---------------------------------------------------------------------------


def test_publish_page_dry_run(monkeypatch):
    with _make_client(monkeypatch, allow_writes=False, allow_publish=False) as client:
        result = client.publish_page("ws-1", "view-1", publish_name="my-page")

    assert result["dry_run"] is True
    assert result["method"] == "POST"
    assert result["path"] == "/api/workspace/ws-1/page-view/view-1/publish"
    assert result["json"]["publish_name"] == "my-page"


def test_publish_page_dry_run_optional_fields(monkeypatch):
    with _make_client(monkeypatch, allow_writes=False, allow_publish=False) as client:
        result = client.publish_page(
            "ws-1",
            "view-1",
            visible_database_view_ids=["db-a", "db-b"],
            comments_enabled=True,
            duplicate_enabled=False,
        )

    assert result["dry_run"] is True
    payload = result["json"]
    assert payload["visible_database_view_ids"] == ["db-a", "db-b"]
    assert payload["comments_enabled"] is True
    assert payload["duplicate_enabled"] is False
    assert "publish_name" not in payload


def test_unpublish_page_dry_run(monkeypatch):
    with _make_client(monkeypatch, allow_writes=False, allow_publish=False) as client:
        result = client.unpublish_page("ws-1", "view-1")

    assert result["dry_run"] is True
    assert result["method"] == "POST"
    assert result["path"] == "/api/workspace/ws-1/page-view/view-1/unpublish"


# ---------------------------------------------------------------------------
# Client: gate enforcement
# ---------------------------------------------------------------------------


def test_publish_page_requires_allow_writes(monkeypatch):
    """APPFLOWY_ALLOW_WRITES=false → AppFlowyError before network call."""
    with (
        _make_client(monkeypatch, allow_writes=False, allow_publish=True) as client,
        pytest.raises(AppFlowyError, match="APPFLOWY_ALLOW_WRITES"),
    ):
        client.publish_page("ws-1", "view-1", dry_run=False)


def test_publish_page_requires_allow_publish_writes(monkeypatch):
    """APPFLOWY_ALLOW_WRITES=true but APPFLOWY_ALLOW_PUBLISH_WRITES=false → AppFlowyError."""
    with (
        _make_client(monkeypatch, allow_writes=True, allow_publish=False) as client,
        pytest.raises(AppFlowyError, match="APPFLOWY_ALLOW_PUBLISH_WRITES"),
    ):
        client.publish_page("ws-1", "view-1", dry_run=False)


def test_unpublish_page_requires_allow_writes(monkeypatch):
    with (
        _make_client(monkeypatch, allow_writes=False, allow_publish=True) as client,
        pytest.raises(AppFlowyError, match="APPFLOWY_ALLOW_WRITES"),
    ):
        client.unpublish_page("ws-1", "view-1", dry_run=False)


def test_unpublish_page_requires_allow_publish_writes(monkeypatch):
    with (
        _make_client(monkeypatch, allow_writes=True, allow_publish=False) as client,
        pytest.raises(AppFlowyError, match="APPFLOWY_ALLOW_PUBLISH_WRITES"),
    ):
        client.unpublish_page("ws-1", "view-1", dry_run=False)


# ---------------------------------------------------------------------------
# Client: live execution (both gates enabled)
# ---------------------------------------------------------------------------


def test_publish_page_live_url_and_payload(monkeypatch):
    seen: list[tuple[str, str, bytes]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path, request.content))
        return httpx.Response(200, json={"data": None, "code": 0})

    with _make_client(
        monkeypatch, allow_writes=True, allow_publish=True, handler=handler
    ) as client:
        result = client.publish_page(
            "ws-1",
            "view-1",
            publish_name="my-slug",
            comments_enabled=False,
            dry_run=False,
        )

    assert len(seen) == 1
    method, path, body = seen[0]
    assert method == "POST"
    assert path == "/api/workspace/ws-1/page-view/view-1/publish"
    payload = json.loads(body)
    assert payload["publish_name"] == "my-slug"
    assert payload["comments_enabled"] is False
    assert result["path"] == path


def test_unpublish_page_live_url(monkeypatch):
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path))
        return httpx.Response(200, json={"data": None, "code": 0})

    with _make_client(
        monkeypatch, allow_writes=True, allow_publish=True, handler=handler
    ) as client:
        result = client.unpublish_page("ws-1", "view-1", dry_run=False)

    assert seen == [("POST", "/api/workspace/ws-1/page-view/view-1/unpublish")]
    assert result["path"] == "/api/workspace/ws-1/page-view/view-1/unpublish"


# ---------------------------------------------------------------------------
# CLI: dry-run (no --execute)
# ---------------------------------------------------------------------------


def test_cli_publish_page_dry_run(monkeypatch, capsys):
    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", "test-token")
    monkeypatch.delenv("APPFLOWY_ALLOW_WRITES", raising=False)
    monkeypatch.delenv("APPFLOWY_ALLOW_PUBLISH_WRITES", raising=False)

    rc = main(
        [
            "publish-page",
            "--workspace-id",
            "ws-1",
            "--view-id",
            "view-1",
            "--publish-name",
            "my-slug",
            "--comments-enabled",
        ]
    )
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["dry_run"] is True
    assert out["path"] == "/api/workspace/ws-1/page-view/view-1/publish"
    assert out["json"]["publish_name"] == "my-slug"
    assert out["json"]["comments_enabled"] is True


def test_cli_publish_page_visible_ids_split(monkeypatch, capsys):
    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", "test-token")

    rc = main(
        [
            "publish-page",
            "--workspace-id",
            "ws-1",
            "--view-id",
            "view-1",
            "--visible-database-view-ids",
            "db-a, db-b, db-c",
        ]
    )
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["json"]["visible_database_view_ids"] == ["db-a", "db-b", "db-c"]


def test_cli_unpublish_page_dry_run(monkeypatch, capsys):
    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", "test-token")

    rc = main(["unpublish-page", "--workspace-id", "ws-1", "--view-id", "view-1"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["dry_run"] is True
    assert out["path"] == "/api/workspace/ws-1/page-view/view-1/unpublish"


def test_cli_publish_page_execute_calls_client(monkeypatch, capsys):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/workspace/ws-1/page-view/view-1/publish"
        return httpx.Response(200, json={"data": None, "code": 0})

    _patch_cli(monkeypatch, handler)
    rc = main(
        [
            "publish-page",
            "--workspace-id",
            "ws-1",
            "--view-id",
            "view-1",
            "--execute",
        ]
    )
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["path"] == "/api/workspace/ws-1/page-view/view-1/publish"


def test_cli_unpublish_page_execute_calls_client(monkeypatch, capsys):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/workspace/ws-1/page-view/view-1/unpublish"
        return httpx.Response(200, json={"data": None, "code": 0})

    _patch_cli(monkeypatch, handler)
    rc = main(["unpublish-page", "--workspace-id", "ws-1", "--view-id", "view-1", "--execute"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["path"] == "/api/workspace/ws-1/page-view/view-1/unpublish"


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------


def test_mcp_publish_page_dry_run():
    with patch("appflowy_mcp_toolkit.mcp.server.AppFlowyClient") as cls:
        instance = cls.return_value.__enter__.return_value
        instance.publish_page.return_value = {
            "dry_run": True,
            "method": "POST",
            "path": "/api/workspace/ws-1/page-view/view-1/publish",
            "json": {},
        }
        raw: Any = asyncio.run(
            mcp.call_tool(
                "appflowy_publish_page",
                {
                    "workspace_id": "ws-1",
                    "view_id": "view-1",
                    "publish_name": "slug",
                    "dry_run": True,
                },
            )
        )
    instance.publish_page.assert_called_once_with(
        "ws-1",
        "view-1",
        publish_name="slug",
        visible_database_view_ids=None,
        comments_enabled=None,
        duplicate_enabled=None,
        dry_run=True,
    )
    result = json.loads(raw[0][0].text)
    assert result["dry_run"] is True


def test_mcp_unpublish_page_dry_run():
    with patch("appflowy_mcp_toolkit.mcp.server.AppFlowyClient") as cls:
        instance = cls.return_value.__enter__.return_value
        instance.unpublish_page.return_value = {
            "dry_run": True,
            "method": "POST",
            "path": "/api/workspace/ws-1/page-view/view-1/unpublish",
        }
        raw: Any = asyncio.run(
            mcp.call_tool(
                "appflowy_unpublish_page",
                {"workspace_id": "ws-1", "view_id": "view-1", "dry_run": True},
            )
        )
    instance.unpublish_page.assert_called_once_with("ws-1", "view-1", dry_run=True)
    result = json.loads(raw[0][0].text)
    assert result["dry_run"] is True


def test_mcp_publish_page_is_write_tool():
    """appflowy_publish_page must not have readOnlyHint=True."""
    tools = asyncio.run(mcp.list_tools())
    tool = next((t for t in tools if t.name == "appflowy_publish_page"), None)
    assert tool is not None
    annotations = tool.annotations
    # readOnlyHint absent or explicitly False
    assert not getattr(annotations, "readOnlyHint", False)


def test_mcp_unpublish_page_is_write_tool():
    tools = asyncio.run(mcp.list_tools())
    tool = next((t for t in tools if t.name == "appflowy_unpublish_page"), None)
    assert tool is not None
    assert not getattr(tool.annotations, "readOnlyHint", False)
