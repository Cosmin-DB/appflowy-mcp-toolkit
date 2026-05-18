"""Unit tests for duplicate_published_page / instantiate_template.

Route confirmed in AppFlowy-Cloud src/api/workspace.rs:
  POST /api/workspace/{workspace_id}/published-duplicate
Payload: { published_view_id, dest_view_id }
Response: { view_id: <root_view_id_for_duplicate> }

Gate: APPFLOWY_ALLOW_WRITES=true only (not the publish gate — this writes to
the user's own workspace, not to a public endpoint).
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


def _patch_client(monkeypatch, handler=None, *, allow_writes: bool = True):
    import httpx as _httpx

    from appflowy_mcp_toolkit import client as client_module

    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("APPFLOWY_ALLOW_WRITES", "true" if allow_writes else "false")

    if handler is not None:
        _real = _httpx.Client

        def fake_client(*a, **kw):
            return _real(transport=_httpx.MockTransport(handler))

        monkeypatch.setattr(client_module.httpx, "Client", fake_client)


# ---------------------------------------------------------------------------
# Client: dry-run
# ---------------------------------------------------------------------------


def test_duplicate_published_page_dry_run(monkeypatch):
    _patch_client(monkeypatch, allow_writes=False)
    from appflowy_mcp_toolkit.client import AppFlowyClient

    with AppFlowyClient() as client:
        result = client.duplicate_published_page(
            "ws-1",
            published_view_id="pub-view-1",
            dest_view_id="dest-view-1",
        )

    assert result["dry_run"] is True
    assert result["method"] == "POST"
    assert result["path"] == "/api/workspace/ws-1/published-duplicate"
    assert result["json"]["published_view_id"] == "pub-view-1"
    assert result["json"]["dest_view_id"] == "dest-view-1"


def test_instantiate_template_dry_run_delegates(monkeypatch):
    _patch_client(monkeypatch, allow_writes=False)
    from appflowy_mcp_toolkit.client import AppFlowyClient

    with AppFlowyClient() as client:
        result = client.instantiate_template(
            "ws-1",
            template_view_id="tmpl-view-1",
            dest_view_id="dest-view-1",
        )

    assert result["dry_run"] is True
    assert result["path"] == "/api/workspace/ws-1/published-duplicate"
    assert result["json"]["published_view_id"] == "tmpl-view-1"


# ---------------------------------------------------------------------------
# Client: gate enforcement
# ---------------------------------------------------------------------------


def test_duplicate_published_page_requires_allow_writes(monkeypatch):
    _patch_client(monkeypatch, allow_writes=False)
    from appflowy_mcp_toolkit.client import AppFlowyClient

    with (
        AppFlowyClient() as client,
        pytest.raises(AppFlowyError, match="APPFLOWY_ALLOW_WRITES"),
    ):
        client.duplicate_published_page(
            "ws-1",
            published_view_id="pub-view-1",
            dest_view_id="dest-view-1",
            dry_run=False,
        )


def test_instantiate_template_requires_allow_writes(monkeypatch):
    _patch_client(monkeypatch, allow_writes=False)
    from appflowy_mcp_toolkit.client import AppFlowyClient

    with (
        AppFlowyClient() as client,
        pytest.raises(AppFlowyError, match="APPFLOWY_ALLOW_WRITES"),
    ):
        client.instantiate_template(
            "ws-1",
            template_view_id="tmpl-view-1",
            dest_view_id="dest-view-1",
            dry_run=False,
        )


def test_duplicate_does_not_require_publish_writes_gate(monkeypatch):
    """APPFLOWY_ALLOW_PUBLISH_WRITES absent → must NOT block duplicate_published_page."""
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, json={"data": {"view_id": "new-view-1"}})

    _patch_client(monkeypatch, handler=handler, allow_writes=True)
    monkeypatch.delenv("APPFLOWY_ALLOW_PUBLISH_WRITES", raising=False)
    from appflowy_mcp_toolkit.client import AppFlowyClient

    with AppFlowyClient() as client:
        result = client.duplicate_published_page(
            "ws-1",
            published_view_id="pub-view-1",
            dest_view_id="dest-view-1",
            dry_run=False,
        )

    assert seen == ["/api/workspace/ws-1/published-duplicate"]
    assert result["view_id"] == "new-view-1"


# ---------------------------------------------------------------------------
# Client: live execution
# ---------------------------------------------------------------------------


def test_duplicate_published_page_live_url_and_payload(monkeypatch):
    seen: list[tuple[str, str, bytes]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path, request.content))
        return httpx.Response(200, json={"data": {"view_id": "new-view-42"}})

    _patch_client(monkeypatch, handler=handler, allow_writes=True)
    from appflowy_mcp_toolkit.client import AppFlowyClient

    with AppFlowyClient() as client:
        result = client.duplicate_published_page(
            "ws-1",
            published_view_id="pub-view-1",
            dest_view_id="dest-view-1",
            dry_run=False,
        )

    assert len(seen) == 1
    method, path, body = seen[0]
    assert method == "POST"
    assert path == "/api/workspace/ws-1/published-duplicate"
    payload = json.loads(body)
    assert payload["published_view_id"] == "pub-view-1"
    assert payload["dest_view_id"] == "dest-view-1"
    assert result["view_id"] == "new-view-42"


# ---------------------------------------------------------------------------
# CLI: dry-run
# ---------------------------------------------------------------------------


def test_cli_duplicate_published_page_dry_run(monkeypatch, capsys):
    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", "test-token")
    monkeypatch.delenv("APPFLOWY_ALLOW_WRITES", raising=False)

    rc = main(
        [
            "duplicate-published-page",
            "--workspace-id",
            "ws-1",
            "--published-view-id",
            "pub-view-1",
            "--dest-view-id",
            "dest-view-1",
        ]
    )
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["dry_run"] is True
    assert out["path"] == "/api/workspace/ws-1/published-duplicate"
    assert out["json"]["published_view_id"] == "pub-view-1"
    assert out["json"]["dest_view_id"] == "dest-view-1"


def test_cli_instantiate_template_dry_run(monkeypatch, capsys):
    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", "test-token")

    rc = main(
        [
            "instantiate-template",
            "--workspace-id",
            "ws-1",
            "--template-view-id",
            "tmpl-view-1",
            "--dest-view-id",
            "dest-view-1",
        ]
    )
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["dry_run"] is True
    assert out["json"]["published_view_id"] == "tmpl-view-1"


def test_cli_duplicate_published_page_execute(monkeypatch, capsys):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/workspace/ws-1/published-duplicate"
        return httpx.Response(200, json={"data": {"view_id": "new-view-1"}})

    _patch_client(monkeypatch, handler=handler, allow_writes=True)
    rc = main(
        [
            "duplicate-published-page",
            "--workspace-id",
            "ws-1",
            "--published-view-id",
            "pub-view-1",
            "--dest-view-id",
            "dest-view-1",
            "--execute",
        ]
    )
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["view_id"] == "new-view-1"


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------


def test_mcp_duplicate_published_page_dry_run():
    with patch("appflowy_mcp_toolkit.mcp.server.AppFlowyClient") as cls:
        instance = cls.return_value.__enter__.return_value
        instance.duplicate_published_page.return_value = {
            "dry_run": True,
            "method": "POST",
            "path": "/api/workspace/ws-1/published-duplicate",
            "json": {"published_view_id": "pub-1", "dest_view_id": "dest-1"},
        }
        raw: Any = asyncio.run(
            mcp.call_tool(
                "appflowy_duplicate_published_page",
                {
                    "workspace_id": "ws-1",
                    "published_view_id": "pub-1",
                    "dest_view_id": "dest-1",
                    "dry_run": True,
                },
            )
        )
    instance.duplicate_published_page.assert_called_once_with(
        "ws-1",
        published_view_id="pub-1",
        dest_view_id="dest-1",
        dry_run=True,
    )
    result = json.loads(raw[0][0].text)
    assert result["dry_run"] is True


def test_mcp_instantiate_template_dry_run():
    with patch("appflowy_mcp_toolkit.mcp.server.AppFlowyClient") as cls:
        instance = cls.return_value.__enter__.return_value
        instance.instantiate_template.return_value = {
            "dry_run": True,
            "path": "/api/workspace/ws-1/published-duplicate",
            "json": {"published_view_id": "tmpl-1", "dest_view_id": "dest-1"},
        }
        raw: Any = asyncio.run(
            mcp.call_tool(
                "appflowy_instantiate_template",
                {
                    "workspace_id": "ws-1",
                    "template_view_id": "tmpl-1",
                    "dest_view_id": "dest-1",
                    "dry_run": True,
                },
            )
        )
    instance.instantiate_template.assert_called_once_with(
        "ws-1",
        template_view_id="tmpl-1",
        dest_view_id="dest-1",
        dry_run=True,
    )
    result = json.loads(raw[0][0].text)
    assert result["dry_run"] is True


def test_mcp_duplicate_and_instantiate_are_write_tools():
    tools = asyncio.run(mcp.list_tools())
    for name in ("appflowy_duplicate_published_page", "appflowy_instantiate_template"):
        tool = next((t for t in tools if t.name == name), None)
        assert tool is not None, f"{name} not registered"
        assert not getattr(tool.annotations, "readOnlyHint", False), f"{name} must not be readOnly"
