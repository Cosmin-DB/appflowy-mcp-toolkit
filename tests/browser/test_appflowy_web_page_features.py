from __future__ import annotations

import os
import time
from contextlib import suppress
from typing import Any

import pytest

from appflowy_mcp_toolkit.client import AppFlowyClient
from appflowy_mcp_toolkit.errors import AppFlowyError
from tests.browser.test_appflowy_web_smoke import (
    ARTIFACT_DIR,
    _app_url,
    _browser_credentials,
    _login,
    _selfhosted_ids,
)

pytestmark = pytest.mark.skipif(
    os.getenv("APPFLOWY_BROWSER_TESTS", "").lower() != "true",
    reason="browser AppFlowy tests are opt-in; set APPFLOWY_BROWSER_TESTS=true",
)

sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright


# Arbitrary AppFlowy template-centre entries are not browser-tested here because
# the local self-hosted stack does not seed a stable public template catalogue.
# The instantiate-template flow is still covered with a disposable published
# page, which exercises the same published-duplicate route without depending on
# AppFlowy Cloud state.


def _extract_id(payload: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    data = payload.get("data")
    if isinstance(data, dict):
        for key in keys:
            value = data.get(key)
            if isinstance(value, str) and value:
                return value
    raise AssertionError(f"Could not extract id from payload keys {keys!r}: {payload!r}")


def _find_first_space_id(node: dict[str, Any]) -> str | None:
    if node.get("is_space") is True and isinstance(node.get("view_id"), str):
        return node["view_id"]
    children = node.get("children")
    if isinstance(children, list):
        for child in children:
            if isinstance(child, dict):
                found = _find_first_space_id(child)
                if found:
                    return found
    return None


def _first_space_id(client: AppFlowyClient, workspace_id: str) -> str:
    folder = client.get_folder(workspace_id, depth=3)
    space_id = _find_first_space_id(folder)
    if not space_id:
        pytest.skip("Could not find a self-hosted AppFlowy space for disposable page tests")
    return space_id


def _open_page(page: Any, workspace_id: str, view_id: str) -> str:
    url = f"{_app_url()}/{workspace_id}/{view_id}"
    last_text = ""
    for _attempt in range(5):
        page.goto(url, wait_until="networkidle", timeout=30_000)
        page.wait_for_timeout(4_000)
        last_text = page.locator("body").inner_text(timeout=15_000)
        if "404 Not Found" not in last_text and "Page not found" not in last_text:
            return last_text
        page.wait_for_timeout(2_000)
    return last_text


def _publish_url(namespace: str, publish_name: str) -> str:
    base_url = (
        os.getenv("APPFLOWY_BROWSER_BASE_URL")
        or os.getenv("APPFLOWY_BASE_URL")
        or "http://localhost"
    )
    return f"{base_url.rstrip('/')}/{namespace}/{publish_name}"


def _public_page_text(
    page: Any,
    namespace: str,
    publish_name: str,
    *,
    expected_text: str | None = None,
) -> str:
    url = _publish_url(namespace, publish_name)
    deadline = time.monotonic() + 30
    last_text = ""
    while time.monotonic() < deadline:
        page.goto(url, wait_until="networkidle", timeout=30_000)
        page.wait_for_timeout(3_000)
        last_text = page.locator("body").inner_text(timeout=15_000)
        if expected_text is None or expected_text in last_text:
            return last_text
        page.wait_for_timeout(1_000)
    return last_text


def test_append_markdown_to_page_visible_in_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPFLOWY_ALLOW_WRITES", "true")
    workspace_id, _database_id = _selfhosted_ids()
    email, password = _browser_credentials()
    suffix = time.time_ns()
    page_name = f"MCP Markdown Browser {suffix}"
    heading = f"Markdown browser heading {suffix}"
    paragraph = f"Markdown browser paragraph {suffix}"
    bullet = f"Markdown browser bullet {suffix}"
    quote = f"Markdown browser quote {suffix}"
    created_view_ids: list[str] = []
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    with AppFlowyClient() as client:
        parent_space_id = _first_space_id(client, workspace_id)
        created = client.create_page_view(
            workspace_id,
            parent_view_id=parent_space_id,
            layout=0,
            name=page_name,
            dry_run=False,
        )
        page_id = _extract_id(created, "view_id", "id")
        created_view_ids.append(page_id)

        try:
            client.append_markdown_to_page(
                workspace_id,
                page_id,
                markdown=f"# {heading}\n\n{paragraph}\n\n- {bullet}\n\n> {quote}",
                dry_run=False,
            )

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    channel="chrome",
                    headless=True,
                    args=["--no-sandbox"],
                )
                page = browser.new_page(viewport={"width": 1365, "height": 768})
                _login(page, email, password)
                body_text = _open_page(page, workspace_id, page_id)
                page.screenshot(
                    path=ARTIFACT_DIR / "page-markdown-append-visible.png",
                    full_page=True,
                )
                browser.close()
        finally:
            for view_id in reversed(created_view_ids):
                with suppress(AppFlowyError):
                    client.move_page_view_to_trash(workspace_id, view_id, dry_run=False)
                with suppress(AppFlowyError):
                    client.delete_page_view_from_trash(workspace_id, view_id, dry_run=False)

    assert heading in body_text
    assert paragraph in body_text
    assert bullet in body_text
    assert quote in body_text


def test_publish_page_visible_on_public_browser_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPFLOWY_ALLOW_WRITES", "true")
    monkeypatch.setenv("APPFLOWY_ALLOW_PUBLISH_WRITES", "true")
    workspace_id, _database_id = _selfhosted_ids()
    suffix = time.time_ns()
    page_name = f"MCP Publish Browser {suffix}"
    heading = f"Publish browser heading {suffix}"
    publish_name = f"publish-browser-{suffix}"
    created_view_ids: list[str] = []
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    with AppFlowyClient() as client:
        parent_space_id = _first_space_id(client, workspace_id)
        created = client.create_page_view(
            workspace_id,
            parent_view_id=parent_space_id,
            layout=0,
            name=page_name,
            dry_run=False,
        )
        page_id = _extract_id(created, "view_id", "id")
        created_view_ids.append(page_id)

        try:
            client.append_markdown_to_page(
                workspace_id,
                page_id,
                markdown=f"# {heading}",
                dry_run=False,
            )
            client.publish_page(
                workspace_id,
                page_id,
                publish_name=publish_name,
                dry_run=False,
            )
            publish_info = client.get_published_page_info(page_id, include_unpublished=True)
            namespace = publish_info.get("namespace")
            assert isinstance(namespace, str) and namespace

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    channel="chrome",
                    headless=True,
                    args=["--no-sandbox"],
                )
                page = browser.new_page(viewport={"width": 1365, "height": 768})
                body_text = _public_page_text(
                    page,
                    namespace,
                    publish_name,
                    expected_text=heading,
                )
                page.screenshot(
                    path=ARTIFACT_DIR / "page-published-public-visible.png",
                    full_page=True,
                )
                browser.close()
        finally:
            with suppress(AppFlowyError):
                client.unpublish_page(workspace_id, page_id, dry_run=False)
            for view_id in reversed(created_view_ids):
                with suppress(AppFlowyError):
                    client.move_page_view_to_trash(workspace_id, view_id, dry_run=False)
                with suppress(AppFlowyError):
                    client.delete_page_view_from_trash(workspace_id, view_id, dry_run=False)

    assert page_name in body_text
    assert heading in body_text


def test_instantiate_template_visible_in_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPFLOWY_ALLOW_WRITES", "true")
    monkeypatch.setenv("APPFLOWY_ALLOW_PUBLISH_WRITES", "true")
    workspace_id, _database_id = _selfhosted_ids()
    email, password = _browser_credentials()
    suffix = time.time_ns()
    source_name = f"MCP Template Source {suffix}"
    heading = f"Instantiated template heading {suffix}"
    publish_name = f"template-source-{suffix}"
    created_view_ids: list[str] = []
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    with AppFlowyClient() as client:
        parent_space_id = _first_space_id(client, workspace_id)
        source = client.create_page_view(
            workspace_id,
            parent_view_id=parent_space_id,
            layout=0,
            name=source_name,
            dry_run=False,
        )
        source_page_id = _extract_id(source, "view_id", "id")
        created_view_ids.append(source_page_id)

        try:
            client.append_markdown_to_page(
                workspace_id,
                source_page_id,
                markdown=f"# {heading}",
                dry_run=False,
            )
            client.publish_page(
                workspace_id,
                source_page_id,
                publish_name=publish_name,
                dry_run=False,
            )
            duplicated = client.instantiate_template(
                workspace_id,
                template_view_id=source_page_id,
                dest_view_id=parent_space_id,
                dry_run=False,
            )
            duplicated_page_id = _extract_id(duplicated, "view_id", "id")
            created_view_ids.append(duplicated_page_id)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    channel="chrome",
                    headless=True,
                    args=["--no-sandbox"],
                )
                page = browser.new_page(viewport={"width": 1365, "height": 768})
                _login(page, email, password)
                body_text = _open_page(page, workspace_id, duplicated_page_id)
                page.screenshot(
                    path=ARTIFACT_DIR / "page-instantiated-template-visible.png",
                    full_page=True,
                )
                browser.close()
        finally:
            with suppress(AppFlowyError):
                client.unpublish_page(workspace_id, source_page_id, dry_run=False)
            for view_id in reversed(created_view_ids):
                with suppress(AppFlowyError):
                    client.move_page_view_to_trash(workspace_id, view_id, dry_run=False)
                with suppress(AppFlowyError):
                    client.delete_page_view_from_trash(workspace_id, view_id, dry_run=False)

    assert heading in body_text
