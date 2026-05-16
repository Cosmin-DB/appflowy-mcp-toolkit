from __future__ import annotations

import os
import time

import pytest

from appflowy_mcp_toolkit.client import AppFlowyClient

pytestmark = pytest.mark.skipif(
    os.getenv("APPFLOWY_SELFHOSTED_TESTS", "").lower() != "true",
    reason="self-hosted AppFlowy tests are opt-in; set APPFLOWY_SELFHOSTED_TESTS=true",
)


def _selfhosted_ids() -> tuple[str, str]:
    base_url = os.getenv("APPFLOWY_BASE_URL", "")
    if "appflowy.cloud" in base_url:
        pytest.fail("self-hosted tests must not target AppFlowy official cloud")
    workspace_id = os.getenv("APPFLOWY_LIVE_WORKSPACE_ID")
    database_id = os.getenv("APPFLOWY_LIVE_DATABASE_ID")
    if not workspace_id or not database_id:
        pytest.skip("APPFLOWY_LIVE_WORKSPACE_ID and APPFLOWY_LIVE_DATABASE_ID are required")
    return workspace_id, database_id


def test_selfhosted_task_lifecycle_data_plane() -> None:
    workspace_id, database_id = _selfhosted_ids()
    task_key = f"selfhosted-smoke-{int(time.time())}"
    description = f"Self-hosted smoke {task_key}"

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
        assert created["verification"]["verified"] is True
        row_id = created["verification"]["row_id"]

        moved = client.move_task(
            workspace_id,
            database_id,
            task_key=task_key,
            status="Doing",
            dry_run=False,
        )
        assert moved["data"] == row_id
        assert moved["verification"]["verified"] is True
        assert moved["verified_row"][0]["cells"]["Status"] == "Doing"

        deleted = client.delete_task(
            workspace_id,
            database_id,
            row_id,
            dry_run=False,
        )
        assert deleted["row_found"] is True
        assert deleted["collab_verified"] is True
        assert deleted["rest_row_list_verified"] is True
