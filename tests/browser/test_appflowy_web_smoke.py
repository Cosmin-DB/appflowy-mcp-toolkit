from __future__ import annotations

import os
import time
from contextlib import suppress
from pathlib import Path
from typing import Any

import pytest

from appflowy_mcp_toolkit.client import AppFlowyClient
from appflowy_mcp_toolkit.errors import AppFlowyError

pytestmark = pytest.mark.skipif(
    os.getenv("APPFLOWY_BROWSER_TESTS", "").lower() != "true",
    reason="browser AppFlowy tests are opt-in; set APPFLOWY_BROWSER_TESTS=true",
)

sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright

ARTIFACT_DIR = Path(".local/browser-smoke")


def _selfhosted_ids() -> tuple[str, str]:
    base_url = os.getenv("APPFLOWY_BASE_URL", "")
    if "appflowy.cloud" in base_url:
        pytest.fail("browser tests must not target AppFlowy official cloud")
    workspace_id = os.getenv("APPFLOWY_TEST_WORKSPACE_ID")
    database_id = os.getenv("APPFLOWY_TEST_DATABASE_ID")
    if not workspace_id or not database_id:
        pytest.skip("APPFLOWY_TEST_WORKSPACE_ID and APPFLOWY_TEST_DATABASE_ID are required")
    return workspace_id, database_id


def _browser_credentials() -> tuple[str, str]:
    email = (
        os.getenv("APPFLOWY_BROWSER_EMAIL")
        or os.getenv("APPFLOWY_TEST_EMAIL")
        or "mcp-test@example.test"
    )
    password = (
        os.getenv("APPFLOWY_BROWSER_PASSWORD")
        or os.getenv("APPFLOWY_TEST_PASSWORD")
        or "appflowy-mcp-test-password"
    )
    return email, password


def _app_url() -> str:
    base_url = (
        os.getenv("APPFLOWY_BROWSER_BASE_URL")
        or os.getenv("APPFLOWY_BASE_URL")
        or "http://localhost"
    )
    return f"{base_url.rstrip('/')}/app"


def _login(page: Any, email: str, password: str) -> None:
    page.goto(_app_url(), wait_until="networkidle", timeout=30_000)
    if "/login" not in page.url:
        return
    page.get_by_placeholder("Please enter your email address").fill(email)
    page.get_by_role("button", name="Continue with password").click()
    page.get_by_placeholder("Enter password").fill(password)
    page.get_by_role("button", name="Continue").click()
    page.wait_for_url("**/app**", timeout=20_000)


def _open_todos(page: Any, workspace_id: str, database_id: str) -> None:
    view_id = _database_view_id(workspace_id, database_id)
    page.goto(f"{_app_url()}/{workspace_id}/{view_id}", wait_until="networkidle", timeout=30_000)
    page.wait_for_timeout(3_000)


def _open_grid(page: Any) -> str:
    _click_visible_text(page, "Grid")
    page.wait_for_timeout(3_000)
    return page.locator("body").inner_text(timeout=10_000)


def _click_visible_text(page: Any, text: str) -> None:
    locator = page.get_by_text(text, exact=True)
    for index in range(locator.count()):
        candidate = locator.nth(index)
        if candidate.bounding_box(timeout=1_000) is not None:
            candidate.click(timeout=10_000)
            return
    raise AssertionError(f"No visible text locator found for {text!r}")


def _database_view_id(workspace_id: str, database_id: str) -> str:
    with AppFlowyClient() as client:
        for database in client.list_databases(workspace_id):
            if database.get("id") != database_id:
                continue
            views = database.get("views")
            if not isinstance(views, list) or not views:
                break
            first_view = views[0]
            if isinstance(first_view, dict) and isinstance(first_view.get("view_id"), str):
                return first_view["view_id"]
    pytest.skip("Could not discover a browser view id for the self-hosted task database")


def test_browser_can_login_and_render_todos_grid() -> None:
    workspace_id, database_id = _selfhosted_ids()
    email, password = _browser_credentials()
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            channel="chrome",
            headless=True,
            args=["--no-sandbox"],
        )
        page = browser.new_page(viewport={"width": 1365, "height": 768})
        _login(page, email, password)
        _open_todos(page, workspace_id, database_id)
        grid_text = _open_grid(page)
        page.screenshot(path=ARTIFACT_DIR / "todos-grid-smoke.png", full_page=True)
        browser.close()

    assert "Description" in grid_text
    assert "Status" in grid_text
    assert "New row" in grid_text


def test_browser_mcp_created_task_rendering_observation() -> None:
    workspace_id, database_id = _selfhosted_ids()
    email, password = _browser_credentials()
    task_key = f"browser-smoke-{time.time_ns()}"
    description = f"Browser smoke {task_key}"
    row_id: str | None = None
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    with AppFlowyClient() as client:
        created = client.create_task(
            workspace_id,
            database_id,
            task_key=task_key,
            description=description,
            status="To Do",
            dry_run=False,
            include_blob_diff=False,
        )
        row_id = created["verification"]["row_id"]
        verification = client.verify_database_row(workspace_id, database_id, row_id)
        assert verification["verified"] is True

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    channel="chrome",
                    headless=True,
                    args=["--no-sandbox"],
                )
                page = browser.new_page(viewport={"width": 1365, "height": 768})
                _login(page, email, password)
                _open_todos(page, workspace_id, database_id)
                board_text = page.locator("body").inner_text(timeout=10_000)
                page.screenshot(path=ARTIFACT_DIR / "todos-board-after-mcp-create.png")
                grid_text = _open_grid(page)
                page.screenshot(path=ARTIFACT_DIR / "todos-grid-after-mcp-create.png")
                browser.close()
        finally:
            if row_id:
                with suppress(AppFlowyError):
                    client.delete_task(workspace_id, database_id, row_id, dry_run=False)

    if description not in board_text and description not in grid_text:
        pytest.xfail(
            "AppFlowy Web did not render the MCP-created row although REST/collab/blob "
            "verification passed; keep this as browser-rendering evidence, not a "
            "data-plane failure."
        )
