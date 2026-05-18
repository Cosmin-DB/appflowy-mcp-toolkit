"""Tests for the Markdown-to-block converter and append_markdown_to_page.

Block types confirmed from AppFlowy-Cloud upstream fixture files:
  libs/workspace-template/assets/initial_document.json  → paragraph, heading, quote,
                                                           numbered_list, todo_list
  libs/workspace-template/assets/desktop_guide.json     → bulleted_list
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
from appflowy_mcp_toolkit.markdown import markdown_to_blocks
from appflowy_mcp_toolkit.mcp.server import mcp

# ---------------------------------------------------------------------------
# Converter unit tests
# ---------------------------------------------------------------------------


def test_paragraph():
    blocks = markdown_to_blocks("Hello world")
    assert len(blocks) == 1
    assert blocks[0]["type"] == "paragraph"
    assert blocks[0]["data"]["delta"] == [{"insert": "Hello world"}]
    assert blocks[0]["children"] == []


def test_heading_levels():
    for level in range(1, 7):
        marker = "#" * level
        blocks = markdown_to_blocks(f"{marker} My heading")
        assert blocks[0]["type"] == "heading"
        assert blocks[0]["data"]["level"] == level
        assert blocks[0]["data"]["delta"] == [{"insert": "My heading"}]


def test_unordered_list_all_markers():
    for marker in ["-", "*", "+"]:
        blocks = markdown_to_blocks(f"{marker} item text")
        assert blocks[0]["type"] == "bulleted_list"
        assert blocks[0]["data"]["delta"] == [{"insert": "item text"}]


def test_ordered_list():
    blocks = markdown_to_blocks("1. First item")
    assert blocks[0]["type"] == "numbered_list"
    assert blocks[0]["data"]["delta"] == [{"insert": "First item"}]

    blocks = markdown_to_blocks("99. Ninety-ninth")
    assert blocks[0]["type"] == "numbered_list"
    assert blocks[0]["data"]["delta"] == [{"insert": "Ninety-ninth"}]


def test_blockquote():
    blocks = markdown_to_blocks("> quoted text")
    assert blocks[0]["type"] == "quote"
    assert blocks[0]["data"]["delta"] == [{"insert": "quoted text"}]


def test_blockquote_no_space():
    blocks = markdown_to_blocks(">also quoted")
    assert blocks[0]["type"] == "quote"
    assert blocks[0]["data"]["delta"] == [{"insert": "also quoted"}]


def test_blank_lines_skipped():
    md = "First\n\nSecond\n\nThird"
    blocks = markdown_to_blocks(md)
    assert len(blocks) == 3
    texts = [b["data"]["delta"][0]["insert"] for b in blocks]
    assert texts == ["First", "Second", "Third"]


def test_mixed_block_types():
    md = "# Title\n\nA paragraph.\n\n- Bullet A\n- Bullet B\n\n1. Item one\n\n> A quote"
    blocks = markdown_to_blocks(md)
    types = [b["type"] for b in blocks]
    assert types == [
        "heading",
        "paragraph",
        "bulleted_list",
        "bulleted_list",
        "numbered_list",
        "quote",
    ]
    assert blocks[0]["data"]["level"] == 1


def test_empty_input_raises():
    with pytest.raises(ValueError):
        markdown_to_blocks("")


def test_whitespace_only_raises():
    with pytest.raises(ValueError):
        markdown_to_blocks("   \n\n   ")


def test_blank_lines_only_raises():
    with pytest.raises(ValueError):
        markdown_to_blocks("\n\n\n")


def test_inline_markdown_not_parsed():
    """Bold/italic/code markers are kept as-is (backlog for rich inline)."""
    blocks = markdown_to_blocks("**bold** and *italic* and `code`")
    assert blocks[0]["type"] == "paragraph"
    assert "**bold**" in blocks[0]["data"]["delta"][0]["insert"]


# ---------------------------------------------------------------------------
# Client: dry-run
# ---------------------------------------------------------------------------


def _setup_env(monkeypatch, *, allow_writes: bool = True):
    import httpx as _httpx

    from appflowy_mcp_toolkit import client as client_module

    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("APPFLOWY_ALLOW_WRITES", "true" if allow_writes else "false")
    return client_module, _httpx


def test_append_markdown_dry_run(monkeypatch):
    _setup_env(monkeypatch, allow_writes=False)
    from appflowy_mcp_toolkit.client import AppFlowyClient

    with AppFlowyClient() as client:
        result = client.append_markdown_to_page(
            "ws-1", "view-1", markdown="# Hello\n\nA paragraph."
        )

    assert result["dry_run"] is True
    assert result["path"] == "/api/workspace/ws-1/page-view/view-1/append-block"
    blocks = result["json"]["blocks"]
    assert blocks[0]["type"] == "heading"
    assert blocks[1]["type"] == "paragraph"


def test_append_markdown_empty_raises(monkeypatch):
    _setup_env(monkeypatch, allow_writes=False)
    from appflowy_mcp_toolkit.client import AppFlowyClient

    with AppFlowyClient() as client, pytest.raises((ValueError, AppFlowyError)):
        client.append_markdown_to_page("ws-1", "view-1", markdown="")


def test_append_markdown_requires_writes(monkeypatch):
    _setup_env(monkeypatch, allow_writes=False)
    from appflowy_mcp_toolkit.client import AppFlowyClient

    with (
        AppFlowyClient() as client,
        pytest.raises(AppFlowyError, match="APPFLOWY_ALLOW_WRITES"),
    ):
        client.append_markdown_to_page("ws-1", "view-1", markdown="Hello", dry_run=False)


def test_append_markdown_live(monkeypatch):
    seen: list[tuple[str, str, bytes]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path, request.content))
        return httpx.Response(200, json={"data": None, "code": 0})

    client_module, _httpx = _setup_env(monkeypatch, allow_writes=True)
    _real = _httpx.Client

    def fake(*a, **kw):
        return _real(transport=_httpx.MockTransport(handler))

    monkeypatch.setattr(client_module.httpx, "Client", fake)
    from appflowy_mcp_toolkit.client import AppFlowyClient

    with AppFlowyClient() as client:
        client.append_markdown_to_page(
            "ws-1", "view-1", markdown="- item A\n- item B", dry_run=False
        )

    assert len(seen) == 1
    method, path, body = seen[0]
    assert method == "POST"
    assert path == "/api/workspace/ws-1/page-view/view-1/append-block"
    payload = json.loads(body)
    assert len(payload["blocks"]) == 2
    assert all(b["type"] == "bulleted_list" for b in payload["blocks"])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _patch_cli(monkeypatch, handler=None, *, allow_writes=True):
    import httpx as _httpx

    from appflowy_mcp_toolkit import client as client_module

    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("APPFLOWY_ALLOW_WRITES", "true" if allow_writes else "false")
    if handler:
        _real = _httpx.Client

        def fake(*a, **kw):
            return _real(transport=_httpx.MockTransport(handler))

        monkeypatch.setattr(client_module.httpx, "Client", fake)


def test_cli_append_markdown_inline_dry_run(monkeypatch, capsys):
    _patch_cli(monkeypatch, allow_writes=False)
    rc = main(
        [
            "append-page-markdown",
            "--workspace-id",
            "ws-1",
            "--view-id",
            "view-1",
            "--markdown",
            "# Heading\n\nParagraph.",
        ]
    )
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["dry_run"] is True
    types = [b["type"] for b in out["json"]["blocks"]]
    assert types == ["heading", "paragraph"]


def test_cli_append_markdown_file_dry_run(monkeypatch, capsys, tmp_path):
    _patch_cli(monkeypatch, allow_writes=False)
    md_file = tmp_path / "input.md"
    md_file.write_text("> A quote\n\n1. Item", encoding="utf-8")

    rc = main(
        [
            "append-page-markdown",
            "--workspace-id",
            "ws-1",
            "--view-id",
            "view-1",
            "--markdown-file",
            str(md_file),
        ]
    )
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["dry_run"] is True
    types = [b["type"] for b in out["json"]["blocks"]]
    assert types == ["quote", "numbered_list"]


def test_cli_append_markdown_mutually_exclusive(monkeypatch, capsys):
    """--markdown and --markdown-file are mutually exclusive."""
    _patch_cli(monkeypatch)
    with pytest.raises(SystemExit):
        main(
            [
                "append-page-markdown",
                "--workspace-id",
                "ws-1",
                "--view-id",
                "view-1",
                "--markdown",
                "text",
                "--markdown-file",
                "path.md",
            ]
        )


def test_cli_append_markdown_execute(monkeypatch, capsys):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/workspace/ws-1/page-view/view-1/append-block"
        return httpx.Response(200, json={"data": None, "code": 0})

    _patch_cli(monkeypatch, handler=handler, allow_writes=True)
    rc = main(
        [
            "append-page-markdown",
            "--workspace-id",
            "ws-1",
            "--view-id",
            "view-1",
            "--markdown",
            "Hello world",
            "--execute",
        ]
    )
    assert rc == 0


# ---------------------------------------------------------------------------
# MCP
# ---------------------------------------------------------------------------


def test_mcp_append_markdown_dry_run():
    with patch("appflowy_mcp_toolkit.mcp.server.AppFlowyClient") as cls:
        instance = cls.return_value.__enter__.return_value
        instance.append_markdown_to_page.return_value = {
            "dry_run": True,
            "method": "POST",
            "path": "/api/workspace/ws-1/page-view/view-1/append-block",
            "json": {
                "blocks": [
                    {"type": "paragraph", "data": {"delta": [{"insert": "Hi"}]}, "children": []}
                ]
            },
        }
        raw: Any = asyncio.run(
            mcp.call_tool(
                "appflowy_append_markdown_to_page",
                {
                    "workspace_id": "ws-1",
                    "view_id": "view-1",
                    "markdown": "Hi",
                    "dry_run": True,
                },
            )
        )
    instance.append_markdown_to_page.assert_called_once_with(
        "ws-1", "view-1", markdown="Hi", dry_run=True
    )
    result = json.loads(raw[0][0].text)
    assert result["dry_run"] is True


def test_mcp_append_markdown_is_write_tool():
    tools = asyncio.run(mcp.list_tools())
    tool = next((t for t in tools if t.name == "appflowy_append_markdown_to_page"), None)
    assert tool is not None
    assert not getattr(tool.annotations, "readOnlyHint", False)
