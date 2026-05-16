from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import patch

from appflowy_mcp_toolkit.mcp.server import mcp

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EXPECTED_READ_TOOLS = {
    "appflowy_health_check",
    "appflowy_get_server_info",
    "appflowy_get_user_profile",
    "appflowy_get_user_workspace_info",
    "appflowy_list_workspaces",
    "appflowy_get_workspace_settings",
    "appflowy_list_workspace_members",
    "appflowy_get_workspace_usage",
    "appflowy_get_file_storage_usage",
    "appflowy_list_file_storage_blobs",
    "appflowy_get_file_metadata",
    "appflowy_get_file_metadata_v1",
    "appflowy_list_recent_views",
    "appflowy_list_favorite_views",
    "appflowy_list_trash_views",
    "appflowy_get_folder",
    "appflowy_get_page_view",
    "appflowy_list_databases",
    "appflowy_get_database_schema",
    "appflowy_list_database_row_ids",
    "appflowy_list_updated_database_rows",
    "appflowy_list_quick_notes",
    "appflowy_get_database_rows",
    "appflowy_search_documents",
    "appflowy_list_select_options",
    "appflowy_get_collab_json",
    "appflowy_get_database_row_orders",
    "appflowy_get_database_blob_diff",
    "appflowy_list_tasks",
    "appflowy_verify_database_row",
}

EXPECTED_WRITE_TOOLS = {
    "appflowy_create_task",
    "appflowy_update_task",
    "appflowy_move_task",
    "appflowy_update_database_row_by_id",
    "appflowy_move_task_by_id",
    "appflowy_delete_task",
    "appflowy_create_quick_note",
    "appflowy_update_quick_note",
    "appflowy_delete_quick_note",
    "appflowy_create_space",
    "appflowy_update_space",
    "appflowy_create_folder_view",
    "appflowy_create_page_view",
    "appflowy_update_page_view",
    "appflowy_rename_page_view",
    "appflowy_favorite_page_view",
    "appflowy_remove_page_icon",
    "appflowy_append_blocks_to_page",
    "appflowy_move_page_view",
    "appflowy_reorder_favorite_page_view",
    "appflowy_duplicate_page_view",
    "appflowy_create_page_database_view",
    "appflowy_trash_page_view",
    "appflowy_restore_page_view",
    "appflowy_delete_trashed_page_view",
    "appflowy_add_recent_pages",
    "appflowy_restore_all_pages_from_trash",
    "appflowy_delete_all_pages_from_trash",
    "appflowy_upload_file_blob_v1",
    "appflowy_delete_file_blob_v1",
    "appflowy_upload_file_as_media",
    "appflowy_create_database_row",
    "appflowy_create_verified_database_row",
    "appflowy_create_typed_database_row",
    "appflowy_create_database_field",
    "appflowy_add_select_option",
    "appflowy_upsert_database_row",
    "appflowy_upsert_typed_database_row",
    "appflowy_upsert_managed_task",
    "appflowy_upsert_verified_managed_task",
    "appflowy_move_managed_task_status",
    "appflowy_delete_database_row",
}

EXPECTED_ALL_TOOLS = EXPECTED_READ_TOOLS | EXPECTED_WRITE_TOOLS


def _get_tools() -> list[Any]:
    return asyncio.run(mcp.list_tools())


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


def test_all_expected_tools_are_registered() -> None:
    tools = _get_tools()
    names = {t.name for t in tools}
    assert names == EXPECTED_ALL_TOOLS, (
        f"Missing: {EXPECTED_ALL_TOOLS - names}  Extra: {names - EXPECTED_ALL_TOOLS}"
    )


def test_read_tools_have_readonly_hint_true() -> None:
    tools = _get_tools()
    for tool in tools:
        if tool.name in EXPECTED_READ_TOOLS:
            assert tool.annotations.readOnlyHint is True, (
                f"{tool.name} should have readOnlyHint=True"
            )


def test_write_tools_have_readonly_hint_false() -> None:
    tools = _get_tools()
    for tool in tools:
        if tool.name in EXPECTED_WRITE_TOOLS:
            assert tool.annotations.readOnlyHint is False, (
                f"{tool.name} should have readOnlyHint=False"
            )


# ---------------------------------------------------------------------------
# Health check smoke via FastMCP.call_tool (no real network)
# ---------------------------------------------------------------------------


def test_health_check_tool_returns_ok_json() -> None:
    """Call appflowy_health_check through FastMCP without real network or secrets."""
    fake_result = {"ok": True, "base_url": "https://example.test"}

    with patch(
        "appflowy_mcp_toolkit.mcp.server.AppFlowyClient",
        autospec=True,
    ) as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.health_check.return_value = fake_result

        raw: Any = asyncio.run(mcp.call_tool("appflowy_health_check", {}))

    content_blocks = raw[0]
    assert len(content_blocks) == 1
    parsed = json.loads(content_blocks[0].text)
    assert parsed == fake_result


def test_updated_rows_tool_delegates_to_client() -> None:
    fake_result = [{"id": "row-1"}]

    with patch(
        "appflowy_mcp_toolkit.mcp.server.AppFlowyClient",
        autospec=True,
    ) as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.list_updated_database_rows.return_value = fake_result

        raw: Any = asyncio.run(
            mcp.call_tool(
                "appflowy_list_updated_database_rows",
                {
                    "workspace_id": "ws",
                    "database_id": "db",
                    "after": "2026-05-16T10:00:00Z",
                },
            )
        )

    instance.list_updated_database_rows.assert_called_once_with(
        "ws",
        "db",
        after="2026-05-16T10:00:00Z",
    )
    content_blocks = raw[0]
    assert json.loads(content_blocks[0].text) == fake_result


def test_quick_note_tools_delegate_to_client() -> None:
    list_result = {"quick_notes": [{"id": "note-1"}], "has_more": False}
    dry_run_result = {"dry_run": True}

    with patch(
        "appflowy_mcp_toolkit.mcp.server.AppFlowyClient",
        autospec=True,
    ) as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.list_quick_notes.return_value = list_result
        instance.create_quick_note.return_value = dry_run_result
        instance.update_quick_note.return_value = dry_run_result
        instance.delete_quick_note.return_value = dry_run_result

        list_raw: Any = asyncio.run(
            mcp.call_tool(
                "appflowy_list_quick_notes",
                {
                    "workspace_id": "ws",
                    "search_term": "pple",
                    "offset": 1,
                    "limit": 2,
                },
            )
        )
        create_raw: Any = asyncio.run(
            mcp.call_tool(
                "appflowy_create_quick_note",
                {
                    "workspace_id": "ws",
                    "data": [{"type": "paragraph"}],
                },
            )
        )
        update_raw: Any = asyncio.run(
            mcp.call_tool(
                "appflowy_update_quick_note",
                {
                    "workspace_id": "ws",
                    "quick_note_id": "note-1",
                    "data": {"text": "updated"},
                },
            )
        )
        delete_raw: Any = asyncio.run(
            mcp.call_tool(
                "appflowy_delete_quick_note",
                {
                    "workspace_id": "ws",
                    "quick_note_id": "note-1",
                },
            )
        )

    instance.list_quick_notes.assert_called_once_with(
        "ws",
        search_term="pple",
        offset=1,
        limit=2,
    )
    instance.create_quick_note.assert_called_once_with(
        "ws",
        data=[{"type": "paragraph"}],
        dry_run=True,
    )
    instance.update_quick_note.assert_called_once_with(
        "ws",
        "note-1",
        data={"text": "updated"},
        dry_run=True,
    )
    instance.delete_quick_note.assert_called_once_with("ws", "note-1", dry_run=True)
    assert json.loads(list_raw[0][0].text) == list_result
    assert json.loads(create_raw[0][0].text) == dry_run_result
    assert json.loads(update_raw[0][0].text) == dry_run_result
    assert json.loads(delete_raw[0][0].text) == dry_run_result


def test_search_documents_tool_delegates_to_client() -> None:
    fake_result = [{"object_id": "page-1", "preview": "project plan"}]

    with patch(
        "appflowy_mcp_toolkit.mcp.server.AppFlowyClient",
        autospec=True,
    ) as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.search_documents.return_value = fake_result

        raw: Any = asyncio.run(
            mcp.call_tool(
                "appflowy_search_documents",
                {
                    "workspace_id": "ws",
                    "query": "project plan",
                    "limit": 5,
                    "preview_size": 120,
                    "score": 0.4,
                },
            )
        )

    instance.search_documents.assert_called_once_with(
        "ws",
        "project plan",
        limit=5,
        preview_size=120,
        score=0.4,
    )
    content_blocks = raw[0]
    assert json.loads(content_blocks[0].text) == fake_result


def test_workspace_readonly_tools_delegate_to_client() -> None:
    with patch(
        "appflowy_mcp_toolkit.mcp.server.AppFlowyClient",
        autospec=True,
    ) as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.get_workspace_settings.return_value = {"workspace_id": "ws", "name": "Demo"}
        instance.list_workspace_members.return_value = [{"email": "demo@example.test"}]
        instance.get_workspace_usage.return_value = {"storage_bytes": 2048}

        settings_raw: Any = asyncio.run(
            mcp.call_tool("appflowy_get_workspace_settings", {"workspace_id": "ws"})
        )
        members_raw: Any = asyncio.run(
            mcp.call_tool("appflowy_list_workspace_members", {"workspace_id": "ws"})
        )
        usage_raw: Any = asyncio.run(
            mcp.call_tool("appflowy_get_workspace_usage", {"workspace_id": "ws"})
        )

    instance.get_workspace_settings.assert_called_once_with("ws")
    instance.list_workspace_members.assert_called_once_with("ws")
    instance.get_workspace_usage.assert_called_once_with("ws")
    assert json.loads(settings_raw[0][0].text) == {"workspace_id": "ws", "name": "Demo"}
    assert json.loads(members_raw[0][0].text) == [{"email": "demo@example.test"}]
    assert json.loads(usage_raw[0][0].text) == {"storage_bytes": 2048}


def test_file_storage_readonly_tools_delegate_to_client() -> None:
    with patch(
        "appflowy_mcp_toolkit.mcp.server.AppFlowyClient",
        autospec=True,
    ) as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.get_file_storage_usage.return_value = {"consumed_capacity": 4096}
        instance.list_file_storage_blobs.return_value = [{"file_id": "file_a"}]
        instance.get_file_metadata.return_value = {"file_id": "file_a", "file_size": 123}
        instance.get_file_metadata_v1.return_value = {"file_id": "file_a", "file_size": 123}

        usage_raw: Any = asyncio.run(
            mcp.call_tool("appflowy_get_file_storage_usage", {"workspace_id": "ws"})
        )
        blobs_raw: Any = asyncio.run(
            mcp.call_tool("appflowy_list_file_storage_blobs", {"workspace_id": "ws"})
        )
        metadata_raw: Any = asyncio.run(
            mcp.call_tool(
                "appflowy_get_file_metadata",
                {"workspace_id": "ws", "file_id": "file_a"},
            )
        )
        metadata_v1_raw: Any = asyncio.run(
            mcp.call_tool(
                "appflowy_get_file_metadata_v1",
                {"workspace_id": "ws", "parent_dir": "parent_a", "file_id": "file_a"},
            )
        )

    instance.get_file_storage_usage.assert_called_once_with("ws")
    instance.list_file_storage_blobs.assert_called_once_with("ws")
    instance.get_file_metadata.assert_called_once_with("ws", "file_a")
    instance.get_file_metadata_v1.assert_called_once_with("ws", "parent_a", "file_a")
    assert json.loads(usage_raw[0][0].text) == {"consumed_capacity": 4096}
    assert json.loads(blobs_raw[0][0].text) == [{"file_id": "file_a"}]
    assert json.loads(metadata_raw[0][0].text) == {"file_id": "file_a", "file_size": 123}
    assert json.loads(metadata_v1_raw[0][0].text) == {"file_id": "file_a", "file_size": 123}


def test_file_storage_write_tools_delegate_to_client() -> None:
    with patch(
        "appflowy_mcp_toolkit.mcp.server.AppFlowyClient",
        autospec=True,
    ) as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.upload_local_file_blob_v1.return_value = {"file_id": "file_a"}
        instance.delete_file_blob_v1.return_value = {"deleted": True}
        instance.upload_file_as_media.return_value = {
            "media": {"url": "https://example.test/file_a", "upload_type": "Cloud"}
        }

        upload_raw: Any = asyncio.run(
            mcp.call_tool(
                "appflowy_upload_file_blob_v1",
                {
                    "workspace_id": "ws",
                    "parent_dir": "db",
                    "file_path": "/tmp/spec.txt",
                    "dry_run": False,
                },
            )
        )
        delete_raw: Any = asyncio.run(
            mcp.call_tool(
                "appflowy_delete_file_blob_v1",
                {
                    "workspace_id": "ws",
                    "parent_dir": "db",
                    "file_id": "file_a",
                    "dry_run": False,
                },
            )
        )
        media_raw: Any = asyncio.run(
            mcp.call_tool(
                "appflowy_upload_file_as_media",
                {
                    "workspace_id": "ws",
                    "database_id": "db",
                    "file_path": "/tmp/spec.txt",
                    "name": "Spec",
                    "dry_run": False,
                },
            )
        )

    instance.upload_local_file_blob_v1.assert_called_once_with(
        "ws",
        "db",
        "/tmp/spec.txt",
        content_type=None,
        dry_run=False,
    )
    instance.delete_file_blob_v1.assert_called_once_with(
        "ws",
        "db",
        "file_a",
        dry_run=False,
    )
    instance.upload_file_as_media.assert_called_once_with(
        "ws",
        "db",
        "/tmp/spec.txt",
        name="Spec",
        content_type=None,
        file_type=None,
        dry_run=False,
    )
    assert json.loads(upload_raw[0][0].text) == {"file_id": "file_a"}
    assert json.loads(delete_raw[0][0].text) == {"deleted": True}
    assert json.loads(media_raw[0][0].text)["media"]["upload_type"] == "Cloud"


def test_navigation_readonly_tools_delegate_to_client() -> None:
    with patch(
        "appflowy_mcp_toolkit.mcp.server.AppFlowyClient",
        autospec=True,
    ) as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.list_recent_views.return_value = [{"view_id": "recent"}]
        instance.list_favorite_views.return_value = [{"view_id": "favorite"}]
        instance.list_trash_views.return_value = [{"view_id": "trash"}]

        recent_raw: Any = asyncio.run(
            mcp.call_tool("appflowy_list_recent_views", {"workspace_id": "ws"})
        )
        favorites_raw: Any = asyncio.run(
            mcp.call_tool("appflowy_list_favorite_views", {"workspace_id": "ws"})
        )
        trash_raw: Any = asyncio.run(
            mcp.call_tool("appflowy_list_trash_views", {"workspace_id": "ws"})
        )

    instance.list_recent_views.assert_called_once_with("ws")
    instance.list_favorite_views.assert_called_once_with("ws")
    instance.list_trash_views.assert_called_once_with("ws")
    assert json.loads(recent_raw[0][0].text) == [{"view_id": "recent"}]
    assert json.loads(favorites_raw[0][0].text) == [{"view_id": "favorite"}]
    assert json.loads(trash_raw[0][0].text) == [{"view_id": "trash"}]


def test_page_view_tools_delegate_to_client() -> None:
    with patch(
        "appflowy_mcp_toolkit.mcp.server.AppFlowyClient",
        autospec=True,
    ) as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.create_space.return_value = {"dry_run": True}
        instance.update_space.return_value = {"dry_run": True}
        instance.create_folder_view.return_value = {"dry_run": True}
        instance.get_page_view.return_value = {"view": {"id": "view1"}}
        instance.create_page_view.return_value = {"dry_run": True}
        instance.update_page_name.return_value = {"dry_run": True}
        instance.move_page_view_to_trash.return_value = {"dry_run": True}

        space_raw: Any = asyncio.run(
            mcp.call_tool(
                "appflowy_create_space",
                {"workspace_id": "ws", "name": "Space"},
            )
        )
        update_space_raw: Any = asyncio.run(
            mcp.call_tool(
                "appflowy_update_space",
                {"workspace_id": "ws", "view_id": "space1", "name": "Space 2"},
            )
        )
        folder_raw: Any = asyncio.run(
            mcp.call_tool(
                "appflowy_create_folder_view",
                {"workspace_id": "ws", "parent_view_id": "parent", "name": "Folder"},
            )
        )
        read_raw: Any = asyncio.run(
            mcp.call_tool("appflowy_get_page_view", {"workspace_id": "ws", "view_id": "view1"})
        )
        create_raw: Any = asyncio.run(
            mcp.call_tool(
                "appflowy_create_page_view",
                {
                    "workspace_id": "ws",
                    "parent_view_id": "parent",
                    "layout": 0,
                    "name": "Page",
                },
            )
        )
        rename_raw: Any = asyncio.run(
            mcp.call_tool(
                "appflowy_rename_page_view",
                {"workspace_id": "ws", "view_id": "view1", "name": "Renamed"},
            )
        )
        trash_raw: Any = asyncio.run(
            mcp.call_tool(
                "appflowy_trash_page_view",
                {"workspace_id": "ws", "view_id": "view1"},
            )
        )

    instance.create_space.assert_called_once_with(
        "ws",
        name="Space",
        space_permission=0,
        space_icon="",
        space_icon_color="",
        view_id=None,
        dry_run=True,
    )
    instance.update_space.assert_called_once_with(
        "ws",
        "space1",
        name="Space 2",
        space_permission=0,
        space_icon="",
        space_icon_color="",
        dry_run=True,
    )
    instance.create_folder_view.assert_called_once_with(
        "ws",
        parent_view_id="parent",
        layout=0,
        name="Folder",
        view_id=None,
        database_id=None,
        dry_run=True,
    )
    instance.get_page_view.assert_called_once_with("ws", "view1")
    instance.create_page_view.assert_called_once_with(
        "ws",
        parent_view_id="parent",
        layout=0,
        name="Page",
        page_data=None,
        view_id=None,
        collab_id=None,
        dry_run=True,
    )
    instance.update_page_name.assert_called_once_with("ws", "view1", name="Renamed", dry_run=True)
    instance.move_page_view_to_trash.assert_called_once_with("ws", "view1", dry_run=True)
    assert json.loads(space_raw[0][0].text) == {"dry_run": True}
    assert json.loads(update_space_raw[0][0].text) == {"dry_run": True}
    assert json.loads(folder_raw[0][0].text) == {"dry_run": True}
    assert json.loads(read_raw[0][0].text) == {"view": {"id": "view1"}}
    assert json.loads(create_raw[0][0].text) == {"dry_run": True}
    assert json.loads(rename_raw[0][0].text) == {"dry_run": True}
    assert json.loads(trash_raw[0][0].text) == {"dry_run": True}
