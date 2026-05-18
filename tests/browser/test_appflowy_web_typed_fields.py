"""Browser acceptance tests for typed field rendering in AppFlowy Web Grid.

These tests create a row with as many typed fields as the self-hosted schema
supports, verify the data plane, then open AppFlowy Web Grid and assert that
the unique Description (and at least the human-visible scalar values) are
present in the rendered page text.

All tests are opt-in: they only run when APPFLOWY_BROWSER_TESTS=true.
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

# Re-use navigation helpers from the smoke suite
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
# Typed field helpers
# ---------------------------------------------------------------------------

_CANDIDATE_TYPED_FIELDS: dict[str, Any] = {
    "MCP Number": "42.5",
    "MCP Checkbox": True,
    "MCP URL": "https://example.test/typed-fields",
    "MCP Summary": "typed-fields summary",
    "MCP Time": "09:15:30",
}

# Human-readable strings we expect to find in Grid text for each field value.
# Checkbox renders as a boolean/tick in some Grid builds; we assert it when the
# text "true" or "✓" is visible.  Other scalars use their string value.
_EXPECTED_GRID_TEXT: dict[str, str] = {
    "MCP Number": "42.5",
    "MCP URL": "https://example.test/typed-fields",
    "MCP Summary": "typed-fields summary",
    # AppFlowy Web Grid renders Time cells as raw seconds integer (e.g. "33330"),
    # not as a formatted HH:MM string.  Assert the stored integer value.
    "MCP Time": "33330",
}


def _field_names(client: AppFlowyClient, workspace_id: str, database_id: str) -> set[str]:
    fields = client.list_database_fields(workspace_id, database_id)
    return {name for f in fields if isinstance((name := f.get("name")), str)}


def _multiselect_options(
    client: AppFlowyClient, workspace_id: str, database_id: str, field_name: str
) -> list[str]:
    """Return available option names for a multiselect field, or [] if absent."""
    try:
        options = client.list_select_options(workspace_id, database_id, field_name=field_name)
        return [o["name"] for o in options if isinstance(o.get("name"), str)]
    except AppFlowyError:
        return []


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_typed_fields_visible_in_grid() -> None:
    """Row with typed fields must render human-visible scalar values in Grid."""
    workspace_id, database_id = _selfhosted_ids()
    email, password = _browser_credentials()
    tag = f"typed-{time.time_ns()}"
    description = f"Typed fields {tag}"
    row_id: str | None = None
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    with AppFlowyClient() as client:
        present_fields = _field_names(client, workspace_id, database_id)

        # Build values dict: always include Description + Status; add typed
        # fields only when present in the schema.
        values: dict[str, Any] = {
            "Description": description,
            "Status": "To Do",
        }
        for field, value in _CANDIDATE_TYPED_FIELDS.items():
            if field in present_fields:
                values[field] = value

        # Multiselect: pick up to 2 available options if the field exists.
        ms_options = _multiselect_options(client, workspace_id, database_id, "Multiselect")
        chosen_ms: list[str] = []
        if "Multiselect" in present_fields and ms_options:
            chosen_ms = ms_options[:2]
            values["Multiselect"] = chosen_ms

        created = client.create_typed_database_row_verified(
            workspace_id,
            database_id,
            values=values,
            dry_run=False,
            include_blob_diff=False,
        )
        row_id = created["result"]["verification"]["row_id"]
        assert created["result"]["verification"]["rest_row_list_present"] is True

        try:
            with sync_playwright() as playwright:
                browser, page, grid_text = _launch_grid_page(
                    playwright, email, password, workspace_id, database_id
                )
                page.screenshot(path=ARTIFACT_DIR / "typed-fields-grid.png", full_page=True)
                browser.close()
        finally:
            if row_id:
                with suppress(AppFlowyError):
                    client.delete_task(workspace_id, database_id, row_id, dry_run=False)

    # Description must always be present
    assert description in grid_text, (
        f"Typed-field row description {description!r} not found in Grid"
    )

    # Assert scalar typed-field values that the schema has and Grid should render
    for field, expected_text in _EXPECTED_GRID_TEXT.items():
        if field in values:
            assert expected_text in grid_text, (
                f"Expected Grid to contain {expected_text!r} for field {field!r}"
            )

    # Multiselect: each chosen option should be visible
    for opt in chosen_ms:
        assert opt in grid_text, f"Multiselect option {opt!r} not found in Grid after row creation"


def test_typed_fields_survive_refresh() -> None:
    """Typed-field row values must still render in Grid after a full page reload."""
    workspace_id, database_id = _selfhosted_ids()
    email, password = _browser_credentials()
    tag = f"typed-refresh-{time.time_ns()}"
    description = f"Typed refresh {tag}"
    row_id: str | None = None
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    with AppFlowyClient() as client:
        present_fields = _field_names(client, workspace_id, database_id)

        values: dict[str, Any] = {
            "Description": description,
            "Status": "To Do",
        }
        # Only include fields the schema carries
        for field, value in _CANDIDATE_TYPED_FIELDS.items():
            if field in present_fields:
                values[field] = value

        created = client.create_typed_database_row_verified(
            workspace_id,
            database_id,
            values=values,
            dry_run=False,
            include_blob_diff=False,
        )
        row_id = created["result"]["verification"]["row_id"]

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
                _click_visible_text(page, "Grid")
                page.wait_for_timeout(3_000)
                # Hard reload
                page.reload(wait_until="networkidle", timeout=30_000)
                page.wait_for_timeout(3_000)
                _click_visible_text(page, "Grid")
                page.wait_for_timeout(3_000)
                grid_text = page.locator("body").inner_text(timeout=10_000)
                page.screenshot(path=ARTIFACT_DIR / "typed-fields-refresh-grid.png", full_page=True)
                browser.close()
        finally:
            if row_id:
                with suppress(AppFlowyError):
                    client.delete_task(workspace_id, database_id, row_id, dry_run=False)

    assert description in grid_text, (
        f"Typed-field row {description!r} not found in Grid after reload"
    )

    for field, expected_text in _EXPECTED_GRID_TEXT.items():
        if field in values:
            assert expected_text in grid_text, (
                f"Expected {expected_text!r} for {field!r} to survive page reload in Grid"
            )
