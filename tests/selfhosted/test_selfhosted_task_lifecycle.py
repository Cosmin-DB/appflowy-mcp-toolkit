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
    workspace_id = os.getenv("APPFLOWY_TEST_WORKSPACE_ID")
    database_id = os.getenv("APPFLOWY_TEST_DATABASE_ID")
    if not workspace_id or not database_id:
        pytest.skip("APPFLOWY_TEST_WORKSPACE_ID and APPFLOWY_TEST_DATABASE_ID are required")
    return workspace_id, database_id


def _extract_id(payload: Any, *keys: str) -> str:
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
        data = payload.get("data")
        if isinstance(data, dict):
            return _extract_id(data, *keys)
    raise AssertionError(f"Could not extract id from payload: {payload!r}")


def _find_first_view(
    tree: dict[str, Any],
    predicate: Callable[[dict[str, Any]], bool],
) -> dict[str, Any] | None:
    if predicate(tree):
        return tree
    children = tree.get("children")
    if isinstance(children, list):
        for child in children:
            if isinstance(child, dict):
                found = _find_first_view(child, predicate)
                if found is not None:
                    return found
    return None


def _find_view_by_id(tree: dict[str, Any], view_id: str) -> dict[str, Any] | None:
    return _find_first_view(tree, lambda view: view.get("view_id") == view_id)


def _require_space_id(client: AppFlowyClient, workspace_id: str) -> str:
    folder = client.get_folder(workspace_id, depth=3)
    space = _find_first_view(folder, lambda view: view.get("is_space") is True)
    if space is None:
        pytest.skip("self-hosted workspace does not contain a space view")
    space_id = space.get("view_id")
    if not isinstance(space_id, str) or not space_id:
        pytest.skip("self-hosted space view did not include a view_id")
    return space_id


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


def _ensure_database_field(
    client: AppFlowyClient,
    workspace_id: str,
    database_id: str,
    *,
    name: str,
    field_type: int,
    type_option_data: dict[str, Any] | None = None,
) -> None:
    def field_exists() -> bool:
        return any(
            field.get("name") == name
            for field in client.list_database_fields(workspace_id, database_id)
        )

    if field_exists():
        return
    client.create_database_field(
        workspace_id,
        database_id,
        name=name,
        field_type=field_type,
        type_option_data=type_option_data,
        dry_run=False,
    )

    def assert_field_exists() -> None:
        assert field_exists()

    _eventually(assert_field_exists)


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


def _delete_views(client: AppFlowyClient, workspace_id: str, view_ids: list[str]) -> None:
    for view_id in reversed(view_ids):
        with suppress(AppFlowyError):
            client.move_page_view_to_trash(workspace_id, view_id, dry_run=False)
        with suppress(AppFlowyError):
            client.delete_page_view_from_trash(workspace_id, view_id, dry_run=False)


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


def test_selfhosted_organizational_structure_lifecycle() -> None:
    workspace_id, _database_id = _selfhosted_ids()
    suffix = time.time_ns()
    created_view_ids: list[str] = []

    with AppFlowyClient() as client:
        parent_space_id = _require_space_id(client, workspace_id)

        try:
            created_space = client.create_space(
                workspace_id,
                name=f"MCP Space {suffix}",
                space_icon="interface_essential/home-3",
                space_icon_color="0xFFA34AFD",
                dry_run=False,
            )
            space_id = _extract_id(created_space, "view_id", "id")
            created_view_ids.append(space_id)

            client.update_space(
                workspace_id,
                space_id,
                name=f"MCP Space Renamed {suffix}",
                space_icon="interface_essential/star",
                space_icon_color="0xFF00AAFF",
                dry_run=False,
            )

            def assert_space_renamed() -> None:
                folder = client.get_folder(workspace_id, depth=3)
                updated_space = _find_view_by_id(folder, space_id)
                assert updated_space is not None
                assert updated_space.get("name") == f"MCP Space Renamed {suffix}"

            _eventually(assert_space_renamed)

            try:
                created_folder = client.create_folder_view(
                    workspace_id,
                    parent_view_id=parent_space_id,
                    layout=0,
                    name=f"MCP Folder {suffix}",
                    dry_run=False,
                )
                folder_id = _extract_id(created_folder, "view_id", "id")
                created_view_ids.append(folder_id)
            except AppFlowyError as exc:
                if exc.status_code != 404:
                    raise
                # The 0.15.17 self-hosted image currently returns 404 for
                # /folder-view although the pinned source route exists. Keep
                # the broader structure smoke running against page/space APIs.
                folder_id = parent_space_id

            created_page = client.create_page_view(
                workspace_id,
                parent_view_id=folder_id,
                layout=0,
                name=f"MCP Page {suffix}",
                dry_run=False,
            )
            page_id = _extract_id(created_page, "view_id", "id")
            created_view_ids.append(page_id)

            client.update_page_name(
                workspace_id,
                page_id,
                name=f"MCP Page Renamed {suffix}",
                dry_run=False,
            )
            client.move_page_view(
                workspace_id,
                page_id,
                new_parent_view_id=parent_space_id,
                dry_run=False,
            )
            client.favorite_page_view(
                workspace_id,
                page_id,
                is_favorite=True,
                dry_run=False,
            )
            client.add_recent_pages(workspace_id, [page_id], dry_run=False)

            def assert_page_moved() -> None:
                folder = client.get_folder(workspace_id, depth=4)
                moved_page = _find_view_by_id(folder, page_id)
                assert moved_page is not None
                assert moved_page.get("name") == f"MCP Page Renamed {suffix}"
                assert moved_page.get("parent_view_id") == parent_space_id

            _eventually(assert_page_moved)

            client.move_page_view_to_trash(workspace_id, page_id, dry_run=False)
            trash = client.list_trash_views(workspace_id)
            assert any(item.get("view_id") == page_id for item in trash)

            client.restore_page_view_from_trash(workspace_id, page_id, dry_run=False)

            def assert_page_restored() -> None:
                folder = client.get_folder(workspace_id, depth=4)
                assert _find_view_by_id(folder, page_id) is not None

            _eventually(assert_page_restored)
        finally:
            _delete_views(client, workspace_id, created_view_ids)


def test_selfhosted_read_surface_smoke() -> None:
    workspace_id, database_id = _selfhosted_ids()

    with AppFlowyClient() as client:
        assert client.health_check()["ok"] is True

        profile = client.get_user_profile()
        assert isinstance(profile.get("email"), str)

        workspace_info = client.get_user_workspace_info()
        assert isinstance(workspace_info, dict)

        workspaces = client.list_workspaces(include_member_count=True, include_role=True)
        assert any(item.get("workspace_id") == workspace_id for item in workspaces)

        settings = client.get_workspace_settings(workspace_id)
        assert isinstance(settings, dict)

        members = client.list_workspace_members(workspace_id)
        assert isinstance(members, list)

        usage = client.get_workspace_usage(workspace_id)
        assert isinstance(usage, dict)

        folder = client.get_folder(workspace_id, depth=2)
        assert isinstance(folder.get("children"), list)

        assert isinstance(client.list_recent_views(workspace_id), list)
        assert isinstance(client.list_favorite_views(workspace_id), list)
        assert isinstance(client.list_trash_views(workspace_id), list)

        databases = client.list_databases(workspace_id)
        assert any(
            _extract_id(database, "database_id", "id", "databaseId") == database_id
            for database in databases
        )

        fields = client.list_database_fields(workspace_id, database_id)
        field_names = {field.get("name") for field in fields}
        assert {"Description", "Status"}.issubset(field_names)

        assert isinstance(client.list_database_row_ids(workspace_id, database_id), list)
        assert isinstance(
            client.list_updated_database_rows(
                workspace_id,
                database_id,
                after="1970-01-01T00:00:00Z",
            ),
            list,
        )
        assert client.get_database_row_orders(workspace_id, database_id)
        assert client.list_select_options(workspace_id, database_id)

        blob_diff = client.get_database_blob_diff_summary(workspace_id, database_id)
        assert "status_name" in blob_diff
        assert isinstance(blob_diff.get("rows"), list)

        quick_notes = client.list_quick_notes(workspace_id, limit=5)
        assert isinstance(quick_notes.get("quick_notes"), list)

        file_usage = client.get_file_storage_usage(workspace_id)
        assert isinstance(file_usage, dict)
        assert isinstance(client.list_file_storage_blobs(workspace_id), list)


def test_selfhosted_quick_note_lifecycle() -> None:
    workspace_id, _database_id = _selfhosted_ids()
    note_id: str | None = None
    suffix = time.time_ns()

    with AppFlowyClient() as client:
        try:
            created = client.create_quick_note(
                workspace_id,
                data=[
                    {
                        "type": "paragraph",
                        "delta": {"insert": f"MCP quick note {suffix}"},
                    }
                ],
                dry_run=False,
            )
            note_id = _extract_id(created, "quick_note_id", "id")

            def assert_note_visible() -> None:
                notes = client.list_quick_notes(workspace_id, search_term=str(suffix), limit=10)
                items = notes.get("quick_notes")
                assert isinstance(items, list)
                assert any(item.get("id") == note_id for item in items if isinstance(item, dict))

            _eventually(assert_note_visible)

            updated = client.update_quick_note(
                workspace_id,
                note_id,
                data=[
                    {
                        "type": "paragraph",
                        "delta": {"insert": f"MCP quick note edited {suffix}"},
                    }
                ],
                dry_run=False,
            )
            assert updated.get("code") == 0

            deleted = client.delete_quick_note(workspace_id, note_id, dry_run=False)
            assert deleted.get("code") == 0
            note_id = None
        finally:
            if note_id is not None:
                with suppress(AppFlowyError):
                    client.delete_quick_note(workspace_id, note_id, dry_run=False)


def test_selfhosted_typed_multifield_row_lifecycle() -> None:
    workspace_id, database_id = _selfhosted_ids()
    suffix = time.time_ns()
    created_row_ids: list[str] = []

    with AppFlowyClient() as client:
        try:
            created = client.create_typed_database_row_verified(
                workspace_id,
                database_id,
                values={
                    "Description": f"Typed multi-field {suffix}",
                    "Status": "To Do",
                    "Multiselect": ["fast", "open source"],
                    "Tasks": [
                        {"name": "Write typed builder", "checked": True},
                        {"name": "Run Docker smoke", "checked": False},
                    ],
                },
                dry_run=False,
                include_blob_diff=False,
            )
            row_id = created["result"]["verification"]["row_id"]
            created_row_ids.append(row_id)
            assert created["typed_cells"]["Status"] == "To Do"
            assert created["typed_cells"]["Multiselect"] == ["fast", "open source"]

            row = _row_by_id(client, workspace_id, database_id, row_id, with_doc=True)
            cells = row["cells"]
            assert cells["Description"] == f"Typed multi-field {suffix}"
            assert cells["Status"] == "To Do"
            assert cells["Multiselect"] == ["fast", "open source"]
            assert cells["Tasks"]["selected_option_ids"] == ["item_0"]

            updated = client.upsert_typed_database_row(
                workspace_id,
                database_id,
                pre_hash=f"typed-multifield-{suffix}",
                values={
                    "Description": f"Typed multi-field updated {suffix}",
                    "Status": "Doing",
                    "Multiselect": ["Q&A", "news"],
                    "Tasks": [
                        {"name": "Write typed builder", "checked": True},
                        {"name": "Run Docker smoke", "checked": True},
                    ],
                },
                dry_run=False,
            )
            updated_row_id = updated["result"]["data"]
            created_row_ids.append(updated_row_id)
            row = _row_by_id(client, workspace_id, database_id, updated_row_id, with_doc=True)
            cells = row["cells"]
            assert cells["Description"] == f"Typed multi-field updated {suffix}"
            assert cells["Status"] == "Doing"
            assert cells["Multiselect"] == ["Q&A", "news"]
            assert cells["Tasks"]["selected_option_ids"] == ["item_0", "item_1"]
        finally:
            _delete_created(client, workspace_id, database_id, created_row_ids)


def test_selfhosted_typed_scalar_field_lifecycle() -> None:
    workspace_id, database_id = _selfhosted_ids()
    suffix = time.time_ns()
    created_row_ids: list[str] = []

    with AppFlowyClient() as client:
        for name, field_type in (
            ("MCP Number", 1),
            ("MCP DateTime", 2),
            ("MCP URL", 6),
            ("MCP Checkbox", 5),
            ("MCP Time", 13),
            ("MCP Summary", 11),
            ("MCP Media", 14),
        ):
            _ensure_database_field(
                client,
                workspace_id,
                database_id,
                name=name,
                field_type=field_type,
            )
        try:
            created = client.create_typed_database_row_verified(
                workspace_id,
                database_id,
                values={
                    "Description": f"Typed scalar fields {suffix}",
                    "Status": "To Do",
                    "MCP Number": "42.5",
                    "MCP DateTime": "2026-05-16T13:00:00+00:00",
                    "MCP URL": "https://example.test/task",
                    "MCP Checkbox": True,
                    "MCP Time": "09:15:30",
                    "MCP Summary": "manual summary",
                    "MCP Media": [
                        {
                            "name": "Spec",
                            "url": "https://example.test/spec.txt",
                            "upload_type": "Network",
                            "file_type": "Text",
                        }
                    ],
                },
                dry_run=False,
                include_blob_diff=False,
            )
            row_id = created["result"]["verification"]["row_id"]
            created_row_ids.append(row_id)
            assert created["typed_cells"]["MCP Number"] == 42.5
            assert created["typed_cells"]["MCP Checkbox"] is True
            assert created["typed_cells"]["MCP Time"] == 33330

            row = _row_by_id(client, workspace_id, database_id, row_id, with_doc=True)
            cells = row["cells"]
            assert cells["Description"] == f"Typed scalar fields {suffix}"
            assert cells["MCP Number"] == "42.5"
            assert cells["MCP DateTime"]["start"] == "2026-05-16T13:00:00+00:00"
            assert cells["MCP URL"] == "https://example.test/task"
            assert cells["MCP Checkbox"] is True
            assert cells["MCP Time"] == 33330
            assert cells["MCP Summary"] == "manual summary"
            assert cells["MCP Media"]["files"][0]["url"] == "https://example.test/spec.txt"
            assert cells["MCP Media"]["files"][0]["upload_type"] == 1
        finally:
            _delete_created(client, workspace_id, database_id, created_row_ids)


def test_selfhosted_media_upload_lifecycle(tmp_path: Path) -> None:
    workspace_id, database_id = _selfhosted_ids()
    suffix = time.time_ns()
    source = tmp_path / "mcp-media.txt"
    source.write_text(f"media payload {suffix}", encoding="utf-8")
    created_row_ids: list[str] = []
    uploaded_file_id: str | None = None

    with AppFlowyClient() as client:
        _ensure_database_field(
            client,
            workspace_id,
            database_id,
            name="MCP Uploaded Media",
            field_type=14,
        )
        try:
            uploaded = client.upload_file_as_media(
                workspace_id,
                database_id,
                source,
                name="Uploaded spec",
                dry_run=False,
            )
            media = uploaded["media"]
            uploaded_file_id = media["id"]
            assert media["upload_type"] == "Cloud"
            assert media["file_type"] == "Text"

            content_type, content = client.get_file_blob_v1(
                workspace_id,
                database_id,
                uploaded_file_id,
            )
            assert content_type.startswith("text/plain")
            assert content.decode("utf-8") == f"media payload {suffix}"

            created = client.create_typed_database_row_verified(
                workspace_id,
                database_id,
                values={
                    "Description": f"Uploaded media field {suffix}",
                    "Status": "To Do",
                    "MCP Uploaded Media": [media],
                },
                dry_run=False,
                include_blob_diff=False,
            )
            row_id = created["result"]["verification"]["row_id"]
            created_row_ids.append(row_id)
            row = _row_by_id(client, workspace_id, database_id, row_id, with_doc=True)
            cells = row["cells"]
            assert cells["MCP Uploaded Media"]["files"][0]["url"] == media["url"]
            assert cells["MCP Uploaded Media"]["files"][0]["upload_type"] == 2
        finally:
            _delete_created(client, workspace_id, database_id, created_row_ids)
            if uploaded_file_id is not None:
                with suppress(AppFlowyError):
                    client.delete_file_blob_v1(
                        workspace_id,
                        database_id,
                        uploaded_file_id,
                        dry_run=False,
                    )


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
