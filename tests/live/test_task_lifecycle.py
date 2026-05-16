from __future__ import annotations

import os
import time

import pytest

from appflowy_mcp_toolkit.client import AppFlowyClient

pytestmark = pytest.mark.skipif(
    os.getenv("APPFLOWY_LIVE_TESTS", "").lower() != "true",
    reason="live AppFlowy tests are opt-in; set APPFLOWY_LIVE_TESTS=true",
)


def _live_ids() -> tuple[str, str]:
    workspace_id = os.getenv("APPFLOWY_LIVE_WORKSPACE_ID")
    database_id = os.getenv("APPFLOWY_LIVE_DATABASE_ID")
    if not workspace_id or not database_id:
        pytest.skip("APPFLOWY_LIVE_WORKSPACE_ID and APPFLOWY_LIVE_DATABASE_ID are required")
    return workspace_id, database_id


def test_managed_task_lifecycle_data_plane() -> None:
    """Create, update/move and delete one disposable task against real AppFlowy.

    This is intentionally not a default unit test. It mutates a configured
    disposable database and verifies the API/collab data plane. AppFlowy Web UI
    rendering is covered by separate browser checks because Board can be stale
    until Grid/refresh warm-up.
    """
    workspace_id, database_id = _live_ids()
    task_key = f"live-smoke-{int(time.time())}"
    description = f"Live smoke {task_key}"

    with AppFlowyClient() as client:
        created = client.upsert_managed_task_verified(
            workspace_id,
            database_id,
            task_key=task_key,
            description=description,
            status="To Do",
            dry_run=False,
            include_blob_diff=False,
        )
        assert created["verification"]["verified"] is True
        row_id = created["verification"]["row_id"]

        moved = client.move_managed_task_status(
            workspace_id,
            database_id,
            task_key=task_key,
            status="Doing",
            dry_run=False,
        )
        assert moved["data"] == row_id
        assert moved["verification"]["verified"] is True
        assert moved["verified_row"][0]["cells"]["Status"] == "Doing"

        deleted = client.delete_database_row_collab(
            workspace_id,
            database_id,
            row_id,
            dry_run=False,
        )
        assert deleted["row_found"] is True
        assert deleted["collab_verified"] is True
        assert deleted["rest_row_list_verified"] is True
