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
* Board column lifecycle tests use a stable MCP-owned Status option id so
  repeated browser runs do not keep adding columns to the disposable database.
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


def _board_view_id(client: AppFlowyClient, workspace_id: str, database_id: str) -> str:
    """Return the Board-layout view id for this database, or skip."""
    for db in client.list_databases(workspace_id):
        if db.get("id") != database_id:
            continue
        for v in db.get("views") or []:
            if isinstance(v, dict) and v.get("layout") == 2:
                view_id = v.get("view_id")
                if isinstance(view_id, str) and view_id:
                    return view_id
    pytest.skip("Could not find a Board view id for the test database")


def _grid_view_id(client: AppFlowyClient, workspace_id: str, database_id: str) -> str:
    """Return the first available view id for this database, or skip."""
    for db in client.list_databases(workspace_id):
        if db.get("id") != database_id:
            continue
        for v in db.get("views") or []:
            if isinstance(v, dict) and isinstance(v.get("view_id"), str):
                return v["view_id"]
    pytest.skip("Could not find a view id for the test database")


def _status_field_id(client: AppFlowyClient, workspace_id: str, database_id: str) -> str:
    """Return the Status field id, or skip when the fixture is not Status-backed."""
    for field in client.list_database_fields(workspace_id, database_id):
        if field.get("name") == "Status" and isinstance(field.get("id"), str):
            return field["id"]
    pytest.skip("Could not find Status field id for the test database")


def _select_option_id_by_name(
    client: AppFlowyClient,
    workspace_id: str,
    database_id: str,
    name: str,
) -> str:
    """Return a Status option id by visible name."""
    for option in client.list_select_options(workspace_id, database_id, field_name="Status"):
        if option.get("name") == name and isinstance(option.get("id"), str):
            return option["id"]
    raise AssertionError(f"Status option {name!r} not found")


def _assert_select_option_id_by_name(
    client: AppFlowyClient,
    workspace_id: str,
    database_id: str,
    name: str,
    expected_option_id: str,
) -> None:
    assert _select_option_id_by_name(client, workspace_id, database_id, name) == expected_option_id


def _eventually(assertion: Any, *, timeout: float = 15.0, interval: float = 1.0) -> None:
    """Retry an assertion while AppFlowy's collab changes settle."""
    deadline = time.monotonic() + timeout
    last_error: AssertionError | None = None
    while time.monotonic() < deadline:
        try:
            assertion()
            return
        except AssertionError as exc:
            last_error = exc
            time.sleep(interval)
    if last_error is not None:
        raise last_error
    assertion()


def _board_group_order(
    client: AppFlowyClient,
    workspace_id: str,
    database_id: str,
    *,
    view_id: str,
    field_id: str,
) -> list[str]:
    """Return visible/raw board group ids for a Status-grouped Board view."""
    collab = client.get_collab_json(
        workspace_id,
        database_id,
        collab_type="Database",
        summary_only=False,
        include_raw=True,
    )
    database = collab.get("collab", {}).get("database", {})
    views = database.get("views", {})
    view = views.get(view_id) if isinstance(views, dict) else None
    if isinstance(view, dict):
        for setting in view.get("groups") or []:
            if not isinstance(setting, dict) or setting.get("field_id") != field_id:
                continue
            return [
                group["id"]
                for group in setting.get("groups") or []
                if isinstance(group, dict) and isinstance(group.get("id"), str)
            ]
    pytest.skip("Could not find board group order for Status field")


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
    _click_view_tab(page, "Grid")
    page.wait_for_timeout(3_000)
    _click_view_tab(page, board_label)
    page.wait_for_timeout(3_000)
    return page.locator("body").inner_text(timeout=10_000)


def _visible_text_candidates(page: Any, text: str) -> list[Any]:
    locator = page.get_by_text(text, exact=True)
    candidates = []
    for index in range(locator.count()):
        candidate = locator.nth(index)
        if candidate.bounding_box(timeout=1_000) is not None:
            candidates.append(candidate)
    return candidates


def _click_view_tab(page: Any, text: str) -> None:
    """Click a database view tab, avoiding matching page titles/sidebar labels."""
    candidates = _visible_text_candidates(page, text)
    if not candidates:
        raise AssertionError(f"No visible text locator found for {text!r}")
    if text == "Grid":
        candidates[0].click(timeout=10_000)
        return

    grid_candidates = _visible_text_candidates(page, "Grid")
    if not grid_candidates:
        candidates[0].click(timeout=10_000)
        return
    grid_box = grid_candidates[0].bounding_box(timeout=1_000)
    if grid_box is None:
        candidates[0].click(timeout=10_000)
        return
    same_row = []
    for candidate in candidates:
        box = candidate.bounding_box(timeout=1_000)
        if box is not None and abs(box["y"] - grid_box["y"]) < 20:
            same_row.append(candidate)
    (same_row[0] if same_row else candidates[0]).click(timeout=10_000)


def _board_text_after_reopen(
    playwright: Any,
    *,
    email: str,
    password: str,
    workspace_id: str,
    database_id: str,
    board_label: str,
    screenshot_name: str,
) -> str:
    """Open the database page, warm Grid -> Board, screenshot, and return body text."""
    browser = playwright.chromium.launch(
        channel="chrome",
        headless=True,
        args=["--no-sandbox"],
    )
    try:
        page = browser.new_page(viewport={"width": 1365, "height": 768})
        _login(page, email, password)
        _open_todos(page, workspace_id, database_id)
        board_text = _open_board_after_grid_warmup(page, board_label)
        with suppress(Exception):
            page.screenshot(
                path=ARTIFACT_DIR / screenshot_name,
                full_page=True,
                timeout=10_000,
            )
        return board_text
    finally:
        # In this AppFlowy Web flow, Chromium can hang during close after a
        # board tab reload. Let Playwright's process teardown clean up instead
        # of turning a passed browser assertion into a stuck test.
        pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_board_status_option_lifecycle_visible_in_browser(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Board shows create/rename/hide/show for a Status option column."""
    monkeypatch.setenv("APPFLOWY_ALLOW_WRITES", "true")
    monkeypatch.setenv("APPFLOWY_ALLOW_COLLAB_WRITES", "true")
    workspace_id, database_id = _selfhosted_ids()
    email, password = _browser_credentials()
    option_id = "mcp_browser_column_lifecycle"
    first_name = "MCP Browser Column Lifecycle"
    renamed_name = "MCP Browser Column Lifecycle Renamed"
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    with AppFlowyClient() as client:
        board_label = _board_tab_label(client, workspace_id, database_id)
        try:
            with suppress(AppFlowyError):
                client.rename_select_option_collab(
                    workspace_id,
                    database_id,
                    option_id=option_id,
                    new_name=first_name,
                    dry_run=False,
                )
            added = client.add_select_option_collab(
                workspace_id,
                database_id,
                name=first_name,
                option_id=option_id,
                dry_run=False,
            )
            assert added["option"]["id"] == option_id
            _eventually(
                lambda: _assert_select_option_id_by_name(
                    client,
                    workspace_id,
                    database_id,
                    first_name,
                    option_id,
                )
            )

            with sync_playwright() as playwright:
                created_text = _board_text_after_reopen(
                    playwright,
                    email=email,
                    password=password,
                    workspace_id=workspace_id,
                    database_id=database_id,
                    board_label=board_label,
                    screenshot_name="board-column-created-visible.png",
                )
            assert first_name in created_text

            renamed = client.rename_select_option_collab(
                workspace_id,
                database_id,
                option_id=option_id,
                new_name=renamed_name,
                dry_run=False,
            )
            assert renamed["renamed"] is True
            _eventually(
                lambda: _assert_select_option_id_by_name(
                    client,
                    workspace_id=workspace_id,
                    database_id=database_id,
                    name=renamed_name,
                    expected_option_id=option_id,
                )
            )

            with sync_playwright() as playwright:
                renamed_text = _board_text_after_reopen(
                    playwright,
                    email=email,
                    password=password,
                    workspace_id=workspace_id,
                    database_id=database_id,
                    board_label=board_label,
                    screenshot_name="board-column-renamed-visible.png",
                )
            assert renamed_name in renamed_text

            hidden = client.set_select_option_visibility_collab(
                workspace_id,
                database_id,
                option_id=option_id,
                visible=False,
                dry_run=False,
            )
            assert hidden["affected_views"]

            with sync_playwright() as playwright:
                hidden_text = _board_text_after_reopen(
                    playwright,
                    email=email,
                    password=password,
                    workspace_id=workspace_id,
                    database_id=database_id,
                    board_label=board_label,
                    screenshot_name="board-column-hidden.png",
                )
            assert renamed_name not in hidden_text

            shown = client.set_select_option_visibility_collab(
                workspace_id,
                database_id,
                option_id=option_id,
                visible=True,
                dry_run=False,
            )
            assert shown["affected_views"]

            with sync_playwright() as playwright:
                shown_text = _board_text_after_reopen(
                    playwright,
                    email=email,
                    password=password,
                    workspace_id=workspace_id,
                    database_id=database_id,
                    board_label=board_label,
                    screenshot_name="board-column-shown-visible.png",
                )
            assert renamed_name in shown_text
        finally:
            with suppress(AppFlowyError):
                client.set_select_option_visibility_collab(
                    workspace_id,
                    database_id,
                    option_id=option_id,
                    visible=True,
                    dry_run=False,
                )
            with suppress(AppFlowyError):
                client.rename_select_option_collab(
                    workspace_id,
                    database_id,
                    option_id=option_id,
                    new_name=first_name,
                    dry_run=False,
                )


def test_board_column_reorder_data_plane_and_browser_presence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Column reorder changes collab order; Board shows the involved columns.

    Browser text order is intentionally not asserted: AppFlowy Web does not
    expose stable column-header positions in body text, and screenshots remain
    the visual artifact. The data-plane group order is the robust order signal.
    """
    monkeypatch.setenv("APPFLOWY_ALLOW_WRITES", "true")
    monkeypatch.setenv("APPFLOWY_ALLOW_COLLAB_WRITES", "true")
    workspace_id, database_id = _selfhosted_ids()
    email, password = _browser_credentials()
    option_id = "mcp_browser_column_reorder"
    option_name = "MCP Browser Column Reorder"
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    with AppFlowyClient() as client:
        board_label = _board_tab_label(client, workspace_id, database_id)
        board_view_id = _board_view_id(client, workspace_id, database_id)
        field_id = _status_field_id(client, workspace_id, database_id)

        added = client.add_select_option_collab(
            workspace_id,
            database_id,
            name=option_name,
            option_id=option_id,
            dry_run=False,
        )
        assert added["option"]["id"] == option_id

        try:
            order_before = _board_group_order(
                client,
                workspace_id,
                database_id,
                view_id=board_view_id,
                field_id=field_id,
            )
            options_by_id = {
                option.get("id"): option.get("name")
                for option in client.list_select_options(
                    workspace_id,
                    database_id,
                    field_name="Status",
                )
                if isinstance(option.get("id"), str) and isinstance(option.get("name"), str)
            }
            anchor_id = next(
                (
                    group_id
                    for group_id in order_before
                    if group_id != option_id and group_id in options_by_id
                ),
                None,
            )
            if anchor_id is None:
                pytest.skip("Need at least one existing Status option group for column reorder")
            anchor_name = options_by_id.get(anchor_id)
            if not isinstance(anchor_name, str):
                pytest.skip("Could not resolve anchor Status group name for browser assertion")

            client.reorder_database_column_collab(
                workspace_id,
                database_id,
                board_view_id,
                field_id,
                option_id,
                before_group_id=None,
                dry_run=False,
            )
            order_before = _board_group_order(
                client,
                workspace_id,
                database_id,
                view_id=board_view_id,
                field_id=field_id,
            )
            anchor_id = next(
                (
                    group_id
                    for group_id in order_before
                    if group_id != option_id and group_id in options_by_id
                ),
                None,
            )
            if anchor_id is None:
                pytest.skip("Need at least one existing Status option group for column reorder")
            anchor_name = options_by_id.get(anchor_id)
            if not isinstance(anchor_name, str):
                pytest.skip("Could not resolve anchor Status group name for browser assertion")

            moved = client.reorder_database_column_collab(
                workspace_id,
                database_id,
                board_view_id,
                field_id,
                option_id,
                before_group_id=anchor_id,
                dry_run=False,
            )
            assert moved["moved"] is True

            order_after = _board_group_order(
                client,
                workspace_id,
                database_id,
                view_id=board_view_id,
                field_id=field_id,
            )
            assert option_id in order_after
            assert anchor_id in order_after
            assert order_after.index(option_id) < order_after.index(anchor_id)

            with sync_playwright() as playwright:
                board_text = _board_text_after_reopen(
                    playwright,
                    email=email,
                    password=password,
                    workspace_id=workspace_id,
                    database_id=database_id,
                    board_label=board_label,
                    screenshot_name="board-column-reorder-presence.png",
                )
        finally:
            with suppress(AppFlowyError):
                client.set_select_option_visibility_collab(
                    workspace_id,
                    database_id,
                    option_id=option_id,
                    visible=True,
                    dry_run=False,
                )

        assert option_name in board_text
        assert anchor_name in board_text


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
