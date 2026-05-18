"""Focused unit tests for AppFlowy publishing metadata reads.

Routes confirmed in AppFlowy-Cloud src/api/workspace.rs:
  GET /api/workspace/{workspace_id}/publish-namespace
  GET /api/workspace/{workspace_id}/publish-default
  GET /api/workspace/{workspace_id}/published-info
  GET /api/workspace/published-info/{view_id}
  GET /api/workspace/v1/published-info/{view_id}

These are metadata reads only. Publish/unpublish mutations are intentionally
not exposed in this slice.
"""

from __future__ import annotations

import json

import httpx

from appflowy_mcp_toolkit.cli.main import main


def _patch_client(monkeypatch, handler, *, access_token: str | None = "test-token"):
    import httpx as _httpx

    from appflowy_mcp_toolkit import client as client_module

    _real_client = _httpx.Client

    def fake_client(*_args, **_kwargs):
        return _real_client(transport=_httpx.MockTransport(handler))

    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    if access_token is None:
        monkeypatch.delenv("APPFLOWY_ACCESS_TOKEN", raising=False)
    else:
        monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", access_token)
    monkeypatch.setattr(client_module.httpx, "Client", fake_client)


def test_publish_namespace_does_not_require_access_token(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/workspace/ws-1/publish-namespace"
        assert "authorization" not in request.headers
        return httpx.Response(200, json={"data": "demo-space"})

    _patch_client(monkeypatch, handler, access_token=None)
    from appflowy_mcp_toolkit.client import AppFlowyClient

    with AppFlowyClient() as client:
        assert client.get_workspace_publish_namespace("ws-1") == "demo-space"


def test_publish_default_url_and_response(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/workspace/ws-1/publish-default"
        return httpx.Response(200, json={"data": {"view_id": "v-1", "publish_name": "home"}})

    _patch_client(monkeypatch, handler)
    from appflowy_mcp_toolkit.client import AppFlowyClient

    with AppFlowyClient() as client:
        result = client.get_workspace_publish_default("ws-1")

    assert result["publish_name"] == "home"


def test_list_published_pages_url_and_response(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/workspace/ws-1/published-info"
        return httpx.Response(
            200,
            json={"data": [{"view_id": "v-1", "publish_name": "home"}]},
        )

    _patch_client(monkeypatch, handler)
    from appflowy_mcp_toolkit.client import AppFlowyClient

    with AppFlowyClient() as client:
        result = client.list_published_pages("ws-1")

    assert result == [{"view_id": "v-1", "publish_name": "home"}]


def test_get_published_page_info_uses_v1_when_requested(monkeypatch):
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(
            200,
            json={"data": {"view_id": "v-1", "unpublished_timestamp": "2026-05-18T00:00:00Z"}},
        )

    _patch_client(monkeypatch, handler)
    from appflowy_mcp_toolkit.client import AppFlowyClient

    with AppFlowyClient() as client:
        result = client.get_published_page_info("v-1", include_unpublished=True)

    assert seen == ["/api/workspace/v1/published-info/v-1"]
    assert result["view_id"] == "v-1"


def test_cli_published_pages(monkeypatch, capsys):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/workspace/ws-1/published-info"
        return httpx.Response(200, json={"data": [{"view_id": "v-1"}]})

    _patch_client(monkeypatch, handler)
    assert main(["published-pages", "--workspace-id", "ws-1"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out[0]["view_id"] == "v-1"


def test_cli_published_page_info_include_unpublished(monkeypatch, capsys):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/workspace/v1/published-info/v-1"
        return httpx.Response(200, json={"data": {"view_id": "v-1"}})

    _patch_client(monkeypatch, handler)
    assert main(["published-page-info", "--view-id", "v-1", "--include-unpublished"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["view_id"] == "v-1"
