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
                page.locator("body").inner_text(timeout=10_000)
                page.screenshot(path=ARTIFACT_DIR / "todos-board-after-mcp-create.png")
                grid_text = _open_grid(page)
                page.screenshot(path=ARTIFACT_DIR / "todos-grid-after-mcp-create.png")
                browser.close()
        finally:
            if row_id:
                with suppress(AppFlowyError):
                    client.delete_task(workspace_id, database_id, row_id, dry_run=False)

    assert description in grid_text


# ---------------------------------------------------------------------------
# Task lifecycle tests
# ---------------------------------------------------------------------------


def _launch_grid_page(
    playwright: Any,
    email: str,
    password: str,
    workspace_id: str,
    database_id: str,
) -> tuple[Any, Any, str]:
    """Return (browser, page, grid_text) with the page open on the Grid view."""
    browser = playwright.chromium.launch(
        channel="chrome",
        headless=True,
        args=["--no-sandbox"],
    )
    page = browser.new_page(viewport={"width": 1365, "height": 768})
    _login(page, email, password)
    _open_todos(page, workspace_id, database_id)
    grid_text = _open_grid(page)
    return browser, page, grid_text


def test_create_task_visible_in_grid() -> None:
    """create_task row must appear in Grid immediately after creation."""
    workspace_id, database_id = _selfhosted_ids()
    email, password = _browser_credentials()
    task_key = f"lifecycle-create-{time.time_ns()}"
    description = f"Lifecycle create {task_key}"
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

        try:
            with sync_playwright() as playwright:
                browser, page, grid_text = _launch_grid_page(
                    playwright, email, password, workspace_id, database_id
                )
                page.screenshot(path=ARTIFACT_DIR / "lifecycle-create-grid.png", full_page=True)
                browser.close()
        finally:
            if row_id:
                with suppress(AppFlowyError):
                    client.delete_task(workspace_id, database_id, row_id, dry_run=False)

    assert description in grid_text, (
        f"Created task description {description!r} not found in Grid after creation"
    )


def test_task_visibility_survives_refresh() -> None:
    """Row must still appear in Grid after a full page reload."""
    workspace_id, database_id = _selfhosted_ids()
    email, password = _browser_credentials()
    task_key = f"lifecycle-refresh-{time.time_ns()}"
    description = f"Lifecycle refresh {task_key}"
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
                _open_grid(page)
                # Hard reload
                page.reload(wait_until="networkidle", timeout=30_000)
                page.wait_for_timeout(3_000)
                grid_text_after_reload = _open_grid(page)
                page.screenshot(
                    path=ARTIFACT_DIR / "lifecycle-refresh-after-reload.png", full_page=True
                )
                browser.close()
        finally:
            if row_id:
                with suppress(AppFlowyError):
                    client.delete_task(workspace_id, database_id, row_id, dry_run=False)

    assert description in grid_text_after_reload, (
        f"Task {description!r} not found in Grid after page reload"
    )


def test_update_description_visible_in_grid() -> None:
    """update_database_row_by_id_collab description change must appear in Grid."""
    workspace_id, database_id = _selfhosted_ids()
    email, password = _browser_credentials()
    task_key = f"lifecycle-desc-{time.time_ns()}"
    original_desc = f"Lifecycle desc-orig {task_key}"
    updated_desc = f"Lifecycle desc-updated {task_key}"
    row_id: str | None = None
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    with AppFlowyClient() as client:
        created = client.create_task(
            workspace_id,
            database_id,
            task_key=task_key,
            description=original_desc,
            status="To Do",
            dry_run=False,
            include_blob_diff=False,
        )
        row_id = created["verification"]["row_id"]

        try:
            client.update_database_row_by_id_collab(
                workspace_id,
                database_id,
                row_id,
                values={"Description": updated_desc},
                dry_run=False,
            )

            with sync_playwright() as playwright:
                browser, page, grid_text = _launch_grid_page(
                    playwright, email, password, workspace_id, database_id
                )
                page.screenshot(
                    path=ARTIFACT_DIR / "lifecycle-desc-updated-grid.png", full_page=True
                )
                browser.close()
        finally:
            if row_id:
                with suppress(AppFlowyError):
                    client.delete_task(workspace_id, database_id, row_id, dry_run=False)

    assert updated_desc in grid_text, f"Updated description {updated_desc!r} not found in Grid"
    assert original_desc not in grid_text, (
        f"Old description {original_desc!r} still visible in Grid after update"
    )


def _pick_non_todo_status(client: AppFlowyClient, workspace_id: str, database_id: str) -> str:
    """Return 'Doing' if present, otherwise the first Status option that is not 'To Do'."""
    options = client.list_select_options(workspace_id, database_id, field_name="Status")
    names = [opt["name"] for opt in options if isinstance(opt.get("name"), str)]
    if "Doing" in names:
        return "Doing"
    fallback = next((n for n in names if n != "To Do"), None)
    if fallback is None:
        pytest.skip("No Status option other than 'To Do' found; cannot run status-update test")
    return fallback


def test_update_status_visible_in_grid() -> None:
    """Status change via update_database_row_by_id_collab must be reflected in Grid."""
    workspace_id, database_id = _selfhosted_ids()
    email, password = _browser_credentials()
    task_key = f"lifecycle-status-{time.time_ns()}"
    description = f"Lifecycle status {task_key}"
    row_id: str | None = None
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    with AppFlowyClient() as client:
        target_status = _pick_non_todo_status(client, workspace_id, database_id)

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

        try:
            client.update_database_row_by_id_collab(
                workspace_id,
                database_id,
                row_id,
                values={"Status": target_status},
                dry_run=False,
            )

            with sync_playwright() as playwright:
                browser, page, grid_text = _launch_grid_page(
                    playwright, email, password, workspace_id, database_id
                )
                page.screenshot(
                    path=ARTIFACT_DIR / "lifecycle-status-updated-grid.png", full_page=True
                )
                browser.close()
        finally:
            if row_id:
                with suppress(AppFlowyError):
                    client.delete_task(workspace_id, database_id, row_id, dry_run=False)

    assert description in grid_text, f"Task {description!r} not found in Grid after status update"
    assert target_status in grid_text, f"Status {target_status!r} not visible in Grid after update"


def test_delete_removes_row_from_grid() -> None:
    """After delete_task, the row must not appear in Grid."""
    workspace_id, database_id = _selfhosted_ids()
    email, password = _browser_credentials()
    task_key = f"lifecycle-delete-{time.time_ns()}"
    description = f"Lifecycle delete {task_key}"
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

        # Delete before opening browser
        client.delete_task(workspace_id, database_id, row_id, dry_run=False)

        with sync_playwright() as playwright:
            browser, page, grid_text = _launch_grid_page(
                playwright, email, password, workspace_id, database_id
            )
            page.screenshot(path=ARTIFACT_DIR / "lifecycle-delete-grid.png", full_page=True)
            browser.close()

    assert description not in grid_text, f"Deleted task {description!r} is still visible in Grid"
