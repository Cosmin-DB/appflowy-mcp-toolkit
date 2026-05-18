"""Focused unit tests for AppFlowy template-center read-only discovery.

Routes confirmed in AppFlowy-Cloud src/api/template.rs:
  GET /api/template-center/category
  GET /api/template-center/category/{category_id}
  GET /api/template-center/creator
  GET /api/template-center/creator/{creator_id}
  GET /api/template-center/template
  GET /api/template-center/template/{view_id}
  GET /api/template-center/homepage

These tests mock httpx transport to verify URL paths, query param encoding,
and response extraction without hitting a real AppFlowy instance.
"""

from __future__ import annotations

import json

import httpx

from appflowy_mcp_toolkit.cli.main import main

# ---------------------------------------------------------------------------
# Shared mock transport helper
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# client method tests
# ---------------------------------------------------------------------------


def test_list_template_categories_url_and_response(monkeypatch):
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(
            200,
            json={
                "data": {
                    "categories": [
                        {"id": "cat-1", "name": "Project Management"},
                        {"id": "cat-2", "name": "CRM"},
                    ]
                }
            },
        )

    _patch_client(monkeypatch, handler)
    from appflowy_mcp_toolkit.client import AppFlowyClient

    with AppFlowyClient() as client:
        result = client.list_template_categories()

    assert seen == ["/api/template-center/category"]
    assert len(result) == 2
    assert result[0]["name"] == "Project Management"


def test_list_template_categories_query_params(monkeypatch):
    seen_params: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_params.update(dict(request.url.params))
        return httpx.Response(200, json={"data": {"categories": []}})

    _patch_client(monkeypatch, handler)
    from appflowy_mcp_toolkit.client import AppFlowyClient

    with AppFlowyClient() as client:
        client.list_template_categories(name_contains="CRM", category_type=1)

    assert seen_params.get("name_contains") == "CRM"
    assert seen_params.get("category_type") == "1"


def test_template_reads_do_not_require_access_token(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert "authorization" not in request.headers
        return httpx.Response(200, json={"data": {"categories": []}})

    _patch_client(monkeypatch, handler, access_token=None)
    from appflowy_mcp_toolkit.client import AppFlowyClient

    with AppFlowyClient() as client:
        assert client.list_template_categories() == []


def test_get_template_category_url(monkeypatch):
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, json={"data": {"id": "cat-1", "name": "CRM"}})

    _patch_client(monkeypatch, handler)
    from appflowy_mcp_toolkit.client import AppFlowyClient

    with AppFlowyClient() as client:
        result = client.get_template_category("cat-1")

    assert seen == ["/api/template-center/category/cat-1"]
    assert result["name"] == "CRM"


def test_list_template_creators_url(monkeypatch):
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(
            200,
            json={"data": {"creators": [{"id": "cr-1", "name": "AppFlowy Team"}]}},
        )

    _patch_client(monkeypatch, handler)
    from appflowy_mcp_toolkit.client import AppFlowyClient

    with AppFlowyClient() as client:
        result = client.list_template_creators()

    assert seen == ["/api/template-center/creator"]
    assert result[0]["name"] == "AppFlowy Team"


def test_get_template_creator_url(monkeypatch):
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, json={"data": {"id": "cr-1", "name": "AppFlowy Team"}})

    _patch_client(monkeypatch, handler)
    from appflowy_mcp_toolkit.client import AppFlowyClient

    with AppFlowyClient() as client:
        result = client.get_template_creator("cr-1")

    assert seen == ["/api/template-center/creator/cr-1"]
    assert result["id"] == "cr-1"


def test_list_templates_url_and_response(monkeypatch):
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(
            200,
            json={
                "data": {
                    "templates": [
                        {"view_id": "v-1", "name": "Sprint Board"},
                        {"view_id": "v-2", "name": "Weekly Planner"},
                    ]
                }
            },
        )

    _patch_client(monkeypatch, handler)
    from appflowy_mcp_toolkit.client import AppFlowyClient

    with AppFlowyClient() as client:
        result = client.list_templates()

    assert seen == ["/api/template-center/template"]
    assert len(result) == 2
    assert result[0]["name"] == "Sprint Board"


def test_list_templates_query_params(monkeypatch):
    seen_params: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_params.update(dict(request.url.params))
        return httpx.Response(200, json={"data": {"templates": []}})

    _patch_client(monkeypatch, handler)
    from appflowy_mcp_toolkit.client import AppFlowyClient

    with AppFlowyClient() as client:
        client.list_templates(
            category_id="cat-1",
            is_featured=True,
            is_new_template=False,
            name_contains="board",
        )

    assert seen_params.get("category_id") == "cat-1"
    assert seen_params.get("is_featured") == "true"
    assert seen_params.get("is_new_template") == "false"
    assert seen_params.get("name_contains") == "board"


def test_get_template_url(monkeypatch):
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(
            200,
            json={"data": {"view_id": "v-abc", "name": "Sprint Board", "description": "..."}},
        )

    _patch_client(monkeypatch, handler)
    from appflowy_mcp_toolkit.client import AppFlowyClient

    with AppFlowyClient() as client:
        result = client.get_template("v-abc")

    assert seen == ["/api/template-center/template/v-abc"]
    assert result["view_id"] == "v-abc"


def test_get_template_homepage_url(monkeypatch):
    seen: list[str] = []
    seen_params: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        seen_params.update(dict(request.url.params))
        return httpx.Response(
            200,
            json={
                "data": {
                    "featured_templates": [{"view_id": "v-1"}],
                    "new_templates": [],
                    "categories": [],
                }
            },
        )

    _patch_client(monkeypatch, handler)
    from appflowy_mcp_toolkit.client import AppFlowyClient

    with AppFlowyClient() as client:
        result = client.get_template_homepage(per_count=5)

    assert seen == ["/api/template-center/homepage"]
    assert seen_params.get("per_count") == "5"
    assert "featured_templates" in result


# ---------------------------------------------------------------------------
# CLI command tests
# ---------------------------------------------------------------------------


def test_cli_template_categories(monkeypatch, capsys):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/template-center/category"
        return httpx.Response(
            200,
            json={"data": {"categories": [{"id": "c1", "name": "PM"}]}},
        )

    _patch_client(monkeypatch, handler)
    assert main(["template-categories"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out[0]["name"] == "PM"


def test_cli_template_categories_with_filters(monkeypatch, capsys):
    seen_params: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_params.update(dict(request.url.params))
        return httpx.Response(200, json={"data": {"categories": []}})

    _patch_client(monkeypatch, handler)
    assert main(["template-categories", "--name-contains", "CRM", "--category-type", "2"]) == 0
    assert seen_params.get("name_contains") == "CRM"
    assert seen_params.get("category_type") == "2"


def test_cli_templates(monkeypatch, capsys):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/template-center/template"
        assert request.url.params.get("is_featured") == "true"
        return httpx.Response(
            200,
            json={"data": {"templates": [{"view_id": "v-1", "name": "Sprint"}]}},
        )

    _patch_client(monkeypatch, handler)
    assert main(["templates", "--is-featured"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out[0]["view_id"] == "v-1"


def test_cli_template(monkeypatch, capsys):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/template-center/template/v-abc"
        return httpx.Response(200, json={"data": {"view_id": "v-abc", "name": "Sprint"}})

    _patch_client(monkeypatch, handler)
    assert main(["template", "--view-id", "v-abc"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["view_id"] == "v-abc"


def test_cli_template_homepage(monkeypatch, capsys):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/template-center/homepage"
        assert request.url.params.get("per_count") == "3"
        return httpx.Response(
            200,
            json={
                "data": {
                    "featured_templates": [],
                    "new_templates": [],
                    "categories": [{"id": "c1"}],
                }
            },
        )

    _patch_client(monkeypatch, handler)
    assert main(["template-homepage", "--per-count", "3"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert "categories" in out


def test_cli_template_creators(monkeypatch, capsys):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/template-center/creator"
        return httpx.Response(
            200,
            json={"data": {"creators": [{"id": "cr-1", "name": "Team"}]}},
        )

    _patch_client(monkeypatch, handler)
    assert main(["template-creators"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out[0]["id"] == "cr-1"
