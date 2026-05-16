from __future__ import annotations

import json
import os
import subprocess
import time
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from typing import Any

import pytest

from appflowy_mcp_toolkit.client import AppFlowyClient
from appflowy_mcp_toolkit.errors import AppFlowyError

pytestmark = pytest.mark.skipif(
    os.getenv("APPFLOWY_SELFHOSTED_TESTS", "").lower() != "true",
    reason="self-hosted AppFlowy tests are opt-in; set APPFLOWY_SELFHOSTED_TESTS=true",
)

ROOT = Path(__file__).resolve().parents[2]
COMPOSE_PROJECT = "appflowy-mcp-test"


def _selfhosted_ids() -> tuple[str, str]:
    base_url = os.getenv("APPFLOWY_BASE_URL", "")
    if "appflowy.cloud" in base_url:
        pytest.fail("self-hosted tests must not target AppFlowy official cloud")
    workspace_id = os.getenv("APPFLOWY_LIVE_WORKSPACE_ID")
    database_id = os.getenv("APPFLOWY_LIVE_DATABASE_ID")
    if not workspace_id or not database_id:
        pytest.skip("APPFLOWY_LIVE_WORKSPACE_ID and APPFLOWY_LIVE_DATABASE_ID are required")
    return workspace_id, database_id


def _task_key(prefix: str) -> str:
    return f"{prefix}-{time.time_ns()}"


def _status_options(client: AppFlowyClient, workspace_id: str, database_id: str) -> list[str]:
    options: list[str] = []
    for item in client.list_select_options(workspace_id, database_id):
        name = item.get("name")
        if isinstance(name, str):
            options.append(name)
    if not options:
        pytest.skip("self-hosted task database has no Status select options")
    return options


def _pick_status(options: list[str], preferred: str, fallback_index: int = 0) -> str:
    if preferred in options:
        return preferred
    return options[min(fallback_index, len(options) - 1)]


def _row_by_id(
    client: AppFlowyClient,
    workspace_id: str,
    database_id: str,
    row_id: str,
    *,
    with_doc: bool = False,
) -> dict[str, Any]:
    rows = client.get_database_rows(workspace_id, database_id, [row_id], with_doc=with_doc)
    assert len(rows) == 1
    return rows[0]


def _cell_contains(row: dict[str, Any], field: str, expected: str) -> bool:
    cells = row.get("cells")
    assert isinstance(cells, dict)
    return expected in json.dumps(cells.get(field), sort_keys=True)


def _assert_row_cells(
    client: AppFlowyClient,
    workspace_id: str,
    database_id: str,
    row_id: str,
    *,
    description: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    row = _row_by_id(client, workspace_id, database_id, row_id, with_doc=True)
    cells = row.get("cells")
    assert isinstance(cells, dict)
    if description is not None:
        assert _cell_contains(row, "Description", description)
    if status is not None:
        assert cells.get("Status") == status
    return row


def _eventually(assertion: Callable[[], Any], *, timeout_seconds: float = 20.0) -> Any:
    deadline = time.monotonic() + timeout_seconds
    last_error: BaseException | None = None
    while time.monotonic() < deadline:
        try:
            return assertion()
        except (AssertionError, AppFlowyError) as exc:
            last_error = exc
            time.sleep(0.5)
    if last_error is not None:
        raise last_error
    raise AssertionError("condition was not evaluated")


def _delete_created(
    client: AppFlowyClient,
    workspace_id: str,
    database_id: str,
    row_ids: list[str],
) -> None:
    for row_id in reversed(row_ids):
        with suppress(AppFlowyError):
            client.delete_task(workspace_id, database_id, row_id, dry_run=False)


def _assert_row_absent_from_list(
    client: AppFlowyClient,
    workspace_id: str,
    database_id: str,
    row_id: str,
) -> None:
    row_ids = {item.get("id") for item in client.list_database_row_ids(workspace_id, database_id)}
    assert row_id not in row_ids


def _row_deleted_assertion(
    client: AppFlowyClient,
    workspace_id: str,
    database_id: str,
    row_id: str,
) -> Callable[[], None]:
    def assert_deleted() -> None:
        row_orders = client.get_database_row_orders(workspace_id, database_id)
        assert all(row_id not in entry.get("row_orders", []) for entry in row_orders)
        _assert_row_absent_from_list(client, workspace_id, database_id, row_id)

    return assert_deleted


def _compose_command() -> list[str]:
    upstream_dir = Path(
        os.getenv("APPFLOWY_CLOUD_DIR", str(ROOT / ".local" / "appflowy-cloud-test"))
    )
    env_file = upstream_dir / ".env"
    compose_file = upstream_dir / "docker-compose.yml"
    override_file = ROOT / "docker" / "appflowy-test" / "compose.override.yml"
    if not env_file.exists() or not compose_file.exists():
        pytest.skip("self-hosted AppFlowy compose files are not present")
    return [
        "docker",
        "compose",
        "--project-name",
        COMPOSE_PROJECT,
        "--env-file",
        str(env_file),
        "-f",
        str(compose_file),
        "-f",
        str(override_file),
    ]


def _require_docker_compose_control() -> list[str]:
    cmd = _compose_command()
    probe = subprocess.run(
        [*cmd, "ps", "--services"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if probe.returncode != 0:
        pytest.skip(f"Docker compose control is unavailable: {probe.stderr.strip()}")
    services = set(probe.stdout.splitlines())
    if "appflowy_cloud" not in services:
        pytest.skip("appflowy_cloud service is not present in the self-hosted compose project")
    return cmd


def _restart_appflowy_service() -> None:
    cmd = _require_docker_compose_control()
    result = subprocess.run(
        [*cmd, "restart", "appflowy_cloud"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"Could not restart appflowy_cloud: {result.stderr.strip()}")


def _wait_for_api(client: AppFlowyClient) -> None:
    def check() -> None:
        assert client.health_check()["ok"] is True

    _eventually(check, timeout_seconds=60.0)


def test_selfhosted_task_lifecycle_data_plane() -> None:
    workspace_id, database_id = _selfhosted_ids()
    task_key = _task_key("selfhosted-smoke")
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

        try:
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
        finally:
            _delete_created(client, workspace_id, database_id, [row_id])


def test_selfhosted_multi_task_lifecycle_with_updates_and_cleanup() -> None:
    workspace_id, database_id = _selfhosted_ids()
    created_row_ids: list[str] = []

    with AppFlowyClient() as client:
        statuses = _status_options(client, workspace_id, database_id)
        todo = _pick_status(statuses, "To Do")
        doing = _pick_status(statuses, "Doing", 1)
        done = _pick_status(statuses, "Done", 2)
        specs = [
            (_task_key("selfhosted-batch-a"), "Batch task A", todo),
            (_task_key("selfhosted-batch-b"), "Batch task B", doing),
            (_task_key("selfhosted-batch-c"), "Batch task C", done),
        ]

        try:
            key_to_row: dict[str, str] = {}
            for task_key, description, status in specs:
                result = client.create_task(
                    workspace_id,
                    database_id,
                    task_key=task_key,
                    description=f"{description} initial {task_key}",
                    status=status,
                    dry_run=False,
                    include_blob_diff=False,
                )
                assert result["verification"]["verified"] is True
                row_id = result["verification"]["row_id"]
                created_row_ids.append(row_id)
                key_to_row[task_key] = row_id
                _assert_row_cells(
                    client,
                    workspace_id,
                    database_id,
                    row_id,
                    description=f"initial {task_key}",
                    status=status,
                )

            assert len(set(created_row_ids)) == len(specs)
            listed = client.list_tasks(workspace_id, database_id)
            listed_ids = set(listed["row_ids"])
            assert set(created_row_ids).issubset(listed_ids)

            first_key, _, _ = specs[0]
            updated_description = f"Batch task A edited {first_key}"
            updated = client.update_task(
                workspace_id,
                database_id,
                task_key=first_key,
                description=updated_description,
                status=done,
                dry_run=False,
                include_blob_diff=False,
            )
            assert updated["verification"]["verified"] is True
            assert updated["verification"]["row_id"] == key_to_row[first_key]
            _assert_row_cells(
                client,
                workspace_id,
                database_id,
                key_to_row[first_key],
                description=updated_description,
                status=done,
            )

            second_key, _, _ = specs[1]
            moved = client.move_task(
                workspace_id,
                database_id,
                task_key=second_key,
                status=todo,
                dry_run=False,
            )
            assert moved["data"] == key_to_row[second_key]
            _assert_row_cells(
                client,
                workspace_id,
                database_id,
                key_to_row[second_key],
                status=todo,
            )

            for row_id in created_row_ids:
                deleted = client.delete_task(workspace_id, database_id, row_id, dry_run=False)
                assert deleted["row_found"] is True
                _eventually(_row_deleted_assertion(client, workspace_id, database_id, row_id))
            created_row_ids.clear()
        finally:
            _delete_created(client, workspace_id, database_id, created_row_ids)


def test_selfhosted_invalid_status_is_rejected_without_mutation() -> None:
    workspace_id, database_id = _selfhosted_ids()
    task_key = _task_key("selfhosted-invalid-status")
    row_ids: list[str] = []

    with AppFlowyClient() as client:
        statuses = _status_options(client, workspace_id, database_id)
        initial_status = _pick_status(statuses, "To Do")
        impossible_status = f"Not A Real Status {time.time_ns()}"

        try:
            created = client.create_task(
                workspace_id,
                database_id,
                task_key=task_key,
                description=f"Invalid status guard {task_key}",
                status=initial_status,
                dry_run=False,
                include_blob_diff=False,
            )
            assert created["verification"]["verified"] is True
            row_id = created["verification"]["row_id"]
            row_ids.append(row_id)

            with pytest.raises(AppFlowyError, match="Invalid Status option"):
                client.move_task(
                    workspace_id,
                    database_id,
                    task_key=task_key,
                    status=impossible_status,
                    dry_run=False,
                )

            _assert_row_cells(
                client,
                workspace_id,
                database_id,
                row_id,
                status=initial_status,
            )
        finally:
            _delete_created(client, workspace_id, database_id, row_ids)


def test_selfhosted_task_persists_across_appflowy_service_restart() -> None:
    workspace_id, database_id = _selfhosted_ids()
    task_key = _task_key("selfhosted-restart")
    row_ids: list[str] = []

    with AppFlowyClient() as client:
        statuses = _status_options(client, workspace_id, database_id)
        doing = _pick_status(statuses, "Doing", 1)
        description = f"Restart persistence {task_key}"
        edited_description = f"Restart persistence edited {task_key}"

        try:
            created = client.create_task(
                workspace_id,
                database_id,
                task_key=task_key,
                description=description,
                status=doing,
                dry_run=False,
                include_blob_diff=False,
            )
            assert created["verification"]["verified"] is True
            row_id = created["verification"]["row_id"]
            row_ids.append(row_id)

            updated = client.update_task(
                workspace_id,
                database_id,
                task_key=task_key,
                description=edited_description,
                status=doing,
                dry_run=False,
                include_blob_diff=False,
            )
            assert updated["verification"]["row_id"] == row_id
            _assert_row_cells(
                client,
                workspace_id,
                database_id,
                row_id,
                description=edited_description,
                status=doing,
            )

            _restart_appflowy_service()
            _wait_for_api(client)

            _eventually(
                lambda: _assert_row_cells(
                    client,
                    workspace_id,
                    database_id,
                    row_id,
                    description=edited_description,
                    status=doing,
                ),
                timeout_seconds=30.0,
            )
        finally:
            _delete_created(client, workspace_id, database_id, row_ids)
