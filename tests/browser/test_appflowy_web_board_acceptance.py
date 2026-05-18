"""Browser acceptance tests for AppFlowy Web Board visibility and ordering.

Tests are opt-in: set APPFLOWY_BROWSER_TESTS=true to run them against a
disposable self-hosted stack.  Do NOT target AppFlowy official cloud.

Discovery notes (self-hosted fixture)
--------------------------------------
* The test database has a single Board-layout view named "To-dos" (layout=2).
* AppFlowy Web shows two tab labels on that page: the Board view name (e.g.
  "To-dos") and "Grid".  There is no tab literally labelled "Board".
* The Board tab label is resolved at runtime from list_databases so the tests
  are not hardcoded to "To-dos".
* Board warm-up pattern: navigate → click Grid tab → click Board tab.
  Without the Grid click, freshly-created rows may not render on Board.
* Row reorder: the collab mutation is confirmed at the data-plane
  (get_database_row_orders).  Grid text-position is not asserted because the
  rendered column headers create ambiguity; see docs/browser-ui-acceptance.md.
"""

from __future__ import annotations

import os
import time
from contextlib import suppress
from pathlib import Path
from typing import Any

import pytest

from appflowy_mcp_toolkit.client import AppFlowyClient
from appflowy_mcp_toolkit.errors import AppFlowyError

# Re-use navigation helpers from the smoke suite.
from tests.browser.test_appflowy_web_smoke import (
    _browser_credentials,
    _click_visible_text,
    _launch_grid_page,
    _login,
    _open_todos,
    _selfhosted_ids,
)

pytestmark = pytest.mark.skipif(
    os.getenv("APPFLOWY_BROWSER_TESTS", "").lower() != "true",
    reason="browser AppFlowy tests are opt-in; set APPFLOWY_BROWSER_TESTS=true",
)

sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright

ARTIFACT_DIR = Path(".local/browser-smoke")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _board_tab_label(client: AppFlowyClient, workspace_id: str, database_id: str) -> str:
    """Return the Board view's tab label (its name in the database views list).

    Walks list_databases to find the first Board-layout (layout=2) view for
    this database.  Falls back to 'Board' if none found.
    """
    for db in client.list_databases(workspace_id):
        if db.get("id") != database_id:
            continue
        for v in db.get("views") or []:
            if isinstance(v, dict) and v.get("layout") == 2:
                name = v.get("name")
                if isinstance(name, str) and name:
                    return name
    return "Board"


def _grid_view_id(client: AppFlowyClient, workspace_id: str, database_id: str) -> str:
    """Return the first available view id for this database, or skip."""
    for db in client.list_databases(workspace_id):
        if db.get("id") != database_id:
            continue
        for v in db.get("views") or []:
            if isinstance(v, dict) and isinstance(v.get("view_id"), str):
                return v["view_id"]
    pytest.skip("Could not find a view id for the test database")


def _pick_non_todo_status(client: AppFlowyClient, workspace_id: str, database_id: str) -> str:
    """Return 'Doing' if present, otherwise the first Status option ≠ 'To Do'."""
    options = client.list_select_options(workspace_id, database_id, field_name="Status")
    names = [o["name"] for o in options if isinstance(o.get("name"), str)]
    if "Doing" in names:
        return "Doing"
    fallback = next((n for n in names if n != "To Do"), None)
    if fallback is None:
        pytest.skip("No Status option other than 'To Do' found; cannot run status test")
    return fallback


def _open_board_after_grid_warmup(page: Any, board_label: str) -> str:
    """Grid warm-up then switch to Board; return Board body text.

    Clicks the Grid tab first (loads fresh data), then clicks the Board tab
    (identified by its view name, e.g. "To-dos").
    """
    _click_visible_text(page, "Grid")
    page.wait_for_timeout(3_000)
    _click_visible_text(page, board_label)
    page.wait_for_timeout(3_000)
    return page.locator("body").inner_text(timeout=10_000)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_board_shows_created_task_after_grid_warmup() -> None:
    """create_task row must appear on the Board after Grid warm-up."""
    workspace_id, database_id = _selfhosted_ids()
    email, password = _browser_credentials()
    tag = f"board-create-{time.time_ns()}"
    description = f"Board create {tag}"
    row_id: str | None = None
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    with AppFlowyClient() as client:
        board_label = _board_tab_label(client, workspace_id, database_id)

        created = client.create_task(
            workspace_id,
            database_id,
            task_key=tag,
            description=description,
            status="To Do",
            dry_run=False,
            include_blob_diff=False,
        )
        row_id = created["verification"]["row_id"]
        assert created["verification"]["rest_row_list_present"] is True

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    channel="chrome", headless=True, args=["--no-sandbox"]
                )
                page = browser.new_page(viewport={"width": 1365, "height": 768})
                _login(page, email, password)
                _open_todos(page, workspace_id, database_id)
                board_text = _open_board_after_grid_warmup(page, board_label)
                page.screenshot(path=ARTIFACT_DIR / "board-create-after-warmup.png", full_page=True)
                browser.close()
        finally:
            if row_id:
                with suppress(AppFlowyError):
                    client.delete_task(workspace_id, database_id, row_id, dry_run=False)

    assert description in board_text, (
        f"Created task {description!r} not found on Board after Grid warm-up"
    )


def test_board_reflects_status_move_after_grid_warmup() -> None:
    """Moving a task to a non-To-Do status must be reflected on the Board."""
    workspace_id, database_id = _selfhosted_ids()
    email, password = _browser_credentials()
    tag = f"board-move-{time.time_ns()}"
    description = f"Board move {tag}"
    row_id: str | None = None
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    with AppFlowyClient() as client:
        target_status = _pick_non_todo_status(client, workspace_id, database_id)
        board_label = _board_tab_label(client, workspace_id, database_id)

        created = client.create_task(
            workspace_id,
            database_id,
            task_key=tag,
            description=description,
            status="To Do",
            dry_run=False,
            include_blob_diff=False,
        )
        row_id = created["verification"]["row_id"]

        try:
            client.move_task_by_row_id(
                workspace_id,
                database_id,
                row_id,
                status=target_status,
                dry_run=False,
            )

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    channel="chrome", headless=True, args=["--no-sandbox"]
                )
                page = browser.new_page(viewport={"width": 1365, "height": 768})
                _login(page, email, password)
                _open_todos(page, workspace_id, database_id)
                board_text = _open_board_after_grid_warmup(page, board_label)
                page.screenshot(path=ARTIFACT_DIR / "board-move-after-warmup.png", full_page=True)
                browser.close()
        finally:
            if row_id:
                with suppress(AppFlowyError):
                    client.delete_task(workspace_id, database_id, row_id, dry_run=False)

    assert description in board_text, (
        f"Moved task {description!r} not found on Board after status move"
    )
    assert target_status in board_text, (
        f"Target status column {target_status!r} not visible on Board after move"
    )


def test_board_row_reorder_data_plane_and_grid_presence() -> None:
    """reorder_database_row_collab changes the data-plane row order; both rows visible in Grid.

    Visual card order in Board is not asserted here: AppFlowy Web Board renders
    cards in DOM order that is not exposed as stable positional text in
    body.inner_text() (column-header rows precede card rows in the text stream,
    making index-based position assertions unreliable).  The data-plane
    verification (get_database_row_orders) is the reliable signal.
    See docs/browser-ui-acceptance.md §Board visual row ordering for the gap note.
    """
    workspace_id, database_id = _selfhosted_ids()
    email, password = _browser_credentials()
    ts = time.time_ns()
    desc_a = f"Reorder-A {ts}"
    desc_b = f"Reorder-B {ts}"
    row_id_a: str | None = None
    row_id_b: str | None = None
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    with AppFlowyClient() as client:
        view_id = _grid_view_id(client, workspace_id, database_id)

        created_a = client.create_task(
            workspace_id,
            database_id,
            task_key=f"reorder-a-{ts}",
            description=desc_a,
            status="To Do",
            dry_run=False,
            include_blob_diff=False,
        )
        row_id_a = created_a["verification"]["row_id"]

        created_b = client.create_task(
            workspace_id,
            database_id,
            task_key=f"reorder-b-{ts}",
            description=desc_b,
            status="To Do",
            dry_run=False,
            include_blob_diff=False,
        )
        row_id_b = created_b["verification"]["row_id"]

        try:
            # Confirm initial data-plane positions
            row_orders_before = client.get_database_row_orders(workspace_id, database_id)
            view_order_before: list[str] = next(
                (e["row_orders"] for e in row_orders_before if e["view_id"] == view_id),
                [],
            )
            idx_a_before = next((i for i, r in enumerate(view_order_before) if r == row_id_a), None)
            idx_b_before = next((i for i, r in enumerate(view_order_before) if r == row_id_b), None)
            if idx_a_before is None or idx_b_before is None:
                pytest.skip(
                    "Newly created rows not found in view row_orders; skipping reorder test"
                )

            # Move B to appear before A
            client.reorder_database_row_collab(
                workspace_id,
                database_id,
                view_id,
                row_id_b,
                before_row_id=row_id_a,
                dry_run=False,
            )

            # Data-plane: B must now precede A
            row_orders_after = client.get_database_row_orders(workspace_id, database_id)
            view_order_after: list[str] = next(
                (e["row_orders"] for e in row_orders_after if e["view_id"] == view_id),
                [],
            )
            idx_a_after = next((i for i, r in enumerate(view_order_after) if r == row_id_a), None)
            idx_b_after = next((i for i, r in enumerate(view_order_after) if r == row_id_b), None)
            assert idx_b_after is not None and idx_a_after is not None, (
                "Row ids missing from view row_orders after reorder"
            )
            assert idx_b_after < idx_a_after, (
                f"Data-plane: expected B (idx {idx_b_after}) before A (idx {idx_a_after})"
            )

            # Browser: both rows must be present in Grid
            with sync_playwright() as playwright:
                browser, page, grid_text = _launch_grid_page(
                    playwright, email, password, workspace_id, database_id
                )
                page.screenshot(path=ARTIFACT_DIR / "board-reorder-grid.png", full_page=True)
                browser.close()

        finally:
            for rid in (row_id_a, row_id_b):
                if rid:
                    with suppress(AppFlowyError):
                        client.delete_task(workspace_id, database_id, rid, dry_run=False)

    assert desc_a in grid_text, f"{desc_a!r} not found in Grid after reorder"
    assert desc_b in grid_text, f"{desc_b!r} not found in Grid after reorder"
