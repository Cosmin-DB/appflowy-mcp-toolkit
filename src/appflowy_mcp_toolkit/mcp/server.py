from __future__ import annotations

from appflowy_mcp_toolkit.client import AppFlowyClient
from appflowy_mcp_toolkit.formatting import compact

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Install MCP extras with: python -m pip install -e '.[mcp]'") from exc

mcp = FastMCP("appflowy-mcp-toolkit")


def _client() -> AppFlowyClient:
    return AppFlowyClient()


@mcp.tool(name="appflowy_health_check", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_health_check() -> str:
    """Check whether AppFlowy is reachable with the configured token."""
    with _client() as client:
        return compact(client.health_check())


@mcp.tool(name="appflowy_list_workspaces", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_list_workspaces(include_member_count: bool = False, include_role: bool = False) -> str:
    """List AppFlowy workspaces visible to the configured account."""
    with _client() as client:
        data = client.list_workspaces(
            include_member_count=include_member_count,
            include_role=include_role,
        )
        return compact(data)


@mcp.tool(name="appflowy_get_server_info", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_get_server_info() -> str:
    """Get public AppFlowy server capability information."""
    with _client() as client:
        return compact(client.get_server_info())


@mcp.tool(name="appflowy_get_user_profile", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_get_user_profile() -> str:
    """Get the authenticated AppFlowy user profile."""
    with _client() as client:
        return compact(client.get_user_profile())


@mcp.tool(name="appflowy_get_user_workspace_info", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_get_user_workspace_info() -> str:
    """Get workspace metadata for the authenticated AppFlowy user."""
    with _client() as client:
        return compact(client.get_user_workspace_info())


@mcp.tool(name="appflowy_get_workspace_settings", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_get_workspace_settings(workspace_id: str) -> str:
    """Get read-only settings for one AppFlowy workspace."""
    with _client() as client:
        return compact(client.get_workspace_settings(workspace_id))


@mcp.tool(name="appflowy_list_workspace_members", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_list_workspace_members(workspace_id: str) -> str:
    """List members for one AppFlowy workspace."""
    with _client() as client:
        return compact(client.list_workspace_members(workspace_id))


@mcp.tool(name="appflowy_get_workspace_usage", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_get_workspace_usage(workspace_id: str) -> str:
    """Get read-only usage information for one AppFlowy workspace."""
    with _client() as client:
        return compact(client.get_workspace_usage(workspace_id))


@mcp.tool(name="appflowy_create_space", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_create_space(
    workspace_id: str,
    name: str,
    space_permission: int = 0,
    space_icon: str = "",
    space_icon_color: str = "",
    view_id: str | None = None,
    dry_run: bool = True,
) -> str:
    """Create an AppFlowy space. Dry-run by default."""
    with _client() as client:
        return compact(
            client.create_space(
                workspace_id,
                name=name,
                space_permission=space_permission,
                space_icon=space_icon,
                space_icon_color=space_icon_color,
                view_id=view_id,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_update_space", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_update_space(
    workspace_id: str,
    view_id: str,
    name: str,
    space_permission: int = 0,
    space_icon: str = "",
    space_icon_color: str = "",
    dry_run: bool = True,
) -> str:
    """Update an AppFlowy space. Dry-run by default."""
    with _client() as client:
        return compact(
            client.update_space(
                workspace_id,
                view_id,
                name=name,
                space_permission=space_permission,
                space_icon=space_icon,
                space_icon_color=space_icon_color,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_get_file_storage_usage", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_get_file_storage_usage(workspace_id: str) -> str:
    """Get read-only file-storage capacity usage for one workspace."""
    with _client() as client:
        return compact(client.get_file_storage_usage(workspace_id))


@mcp.tool(name="appflowy_list_file_storage_blobs", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_list_file_storage_blobs(workspace_id: str) -> str:
    """List file-storage blob metadata for one workspace without fetching blob bytes."""
    with _client() as client:
        return compact(client.list_file_storage_blobs(workspace_id))


@mcp.tool(name="appflowy_get_file_metadata", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_get_file_metadata(workspace_id: str, file_id: str) -> str:
    """Get v0 file metadata by file id without downloading blob content."""
    with _client() as client:
        return compact(client.get_file_metadata(workspace_id, file_id))


@mcp.tool(name="appflowy_get_file_metadata_v1", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_get_file_metadata_v1(workspace_id: str, parent_dir: str, file_id: str) -> str:
    """Get v1 file metadata by parent directory and file id without blob content."""
    with _client() as client:
        return compact(client.get_file_metadata_v1(workspace_id, parent_dir, file_id))


@mcp.tool(name="appflowy_upload_file_blob_v1", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_upload_file_blob_v1(
    workspace_id: str,
    parent_dir: str,
    file_path: str,
    content_type: str | None = None,
    dry_run: bool = True,
) -> str:
    """Upload a local file to AppFlowy v1 file storage. Dry-run by default."""
    with _client() as client:
        return compact(
            client.upload_local_file_blob_v1(
                workspace_id,
                parent_dir,
                file_path,
                content_type=content_type,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_delete_file_blob_v1", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_delete_file_blob_v1(
    workspace_id: str,
    parent_dir: str,
    file_id: str,
    dry_run: bool = True,
) -> str:
    """Delete a v1 file-storage blob. Dry-run by default."""
    with _client() as client:
        return compact(
            client.delete_file_blob_v1(
                workspace_id,
                parent_dir,
                file_id,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_upload_file_as_media", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_upload_file_as_media(
    workspace_id: str,
    database_id: str,
    file_path: str,
    name: str | None = None,
    content_type: str | None = None,
    file_type: str | None = None,
    dry_run: bool = True,
) -> str:
    """Upload a local file and return a typed Media-cell object. Dry-run by default."""
    with _client() as client:
        return compact(
            client.upload_file_as_media(
                workspace_id,
                database_id,
                file_path,
                name=name,
                content_type=content_type,
                file_type=file_type,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_get_folder", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_get_folder(
    workspace_id: str,
    depth: int | None = None,
    root_view_id: str | None = None,
) -> str:
    """Get a workspace folder/view tree or subtree."""
    with _client() as client:
        return compact(client.get_folder(workspace_id, depth=depth, root_view_id=root_view_id))


@mcp.tool(name="appflowy_create_folder_view", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_create_folder_view(
    workspace_id: str,
    parent_view_id: str,
    layout: int = 0,
    name: str | None = None,
    view_id: str | None = None,
    database_id: str | None = None,
    dry_run: bool = True,
) -> str:
    """Create a folder view. Dry-run by default."""
    with _client() as client:
        return compact(
            client.create_folder_view(
                workspace_id,
                parent_view_id=parent_view_id,
                layout=layout,
                name=name,
                view_id=view_id,
                database_id=database_id,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_get_page_view", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_get_page_view(workspace_id: str, view_id: str) -> str:
    """Get a page/view collab payload by view id."""
    with _client() as client:
        return compact(client.get_page_view(workspace_id, view_id))


@mcp.tool(name="appflowy_create_page_view", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_create_page_view(
    workspace_id: str,
    parent_view_id: str,
    layout: int = 0,
    name: str | None = None,
    page_data: dict | None = None,
    view_id: str | None = None,
    collab_id: str | None = None,
    dry_run: bool = True,
) -> str:
    """Create an AppFlowy page view. Dry-run by default."""
    with _client() as client:
        return compact(
            client.create_page_view(
                workspace_id,
                parent_view_id=parent_view_id,
                layout=layout,
                name=name,
                page_data=page_data,
                view_id=view_id,
                collab_id=collab_id,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_update_page_view", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_update_page_view(
    workspace_id: str,
    view_id: str,
    name: str,
    icon: dict | None = None,
    is_locked: bool | None = None,
    extra: dict | None = None,
    dry_run: bool = True,
) -> str:
    """Update page metadata. Dry-run by default."""
    with _client() as client:
        return compact(
            client.update_page_view(
                workspace_id,
                view_id,
                name=name,
                icon=icon,
                is_locked=is_locked,
                extra=extra,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_rename_page_view", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_rename_page_view(
    workspace_id: str,
    view_id: str,
    name: str,
    dry_run: bool = True,
) -> str:
    """Rename a page view. Dry-run by default."""
    with _client() as client:
        return compact(client.update_page_name(workspace_id, view_id, name=name, dry_run=dry_run))


@mcp.tool(name="appflowy_favorite_page_view", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_favorite_page_view(
    workspace_id: str,
    view_id: str,
    is_favorite: bool = True,
    is_pinned: bool = False,
    dry_run: bool = True,
) -> str:
    """Add/remove a page from favorites. Dry-run by default."""
    with _client() as client:
        return compact(
            client.favorite_page_view(
                workspace_id,
                view_id,
                is_favorite=is_favorite,
                is_pinned=is_pinned,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_remove_page_icon", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_remove_page_icon(workspace_id: str, view_id: str, dry_run: bool = True) -> str:
    """Remove a page icon. Dry-run by default."""
    with _client() as client:
        return compact(client.remove_page_icon(workspace_id, view_id, dry_run=dry_run))


@mcp.tool(name="appflowy_append_blocks_to_page", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_append_blocks_to_page(
    workspace_id: str,
    view_id: str,
    blocks: list[dict],
    dry_run: bool = True,
) -> str:
    """Append raw AppFlowy block JSON objects to a page. Dry-run by default."""
    with _client() as client:
        return compact(
            client.append_blocks_to_page(
                workspace_id,
                view_id,
                blocks=blocks,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_move_page_view", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_move_page_view(
    workspace_id: str,
    view_id: str,
    new_parent_view_id: str,
    prev_view_id: str | None = None,
    dry_run: bool = True,
) -> str:
    """Move a page under a new parent. Dry-run by default."""
    with _client() as client:
        return compact(
            client.move_page_view(
                workspace_id,
                view_id,
                new_parent_view_id=new_parent_view_id,
                prev_view_id=prev_view_id,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_reorder_favorite_page_view", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_reorder_favorite_page_view(
    workspace_id: str,
    view_id: str,
    prev_view_id: str | None = None,
    dry_run: bool = True,
) -> str:
    """Reorder a favorite page. Dry-run by default."""
    with _client() as client:
        return compact(
            client.reorder_favorite_page_view(
                workspace_id,
                view_id,
                prev_view_id=prev_view_id,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_duplicate_page_view", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_duplicate_page_view(
    workspace_id: str,
    view_id: str,
    suffix: str | None = None,
    dry_run: bool = True,
) -> str:
    """Duplicate a page tree. Dry-run by default."""
    with _client() as client:
        return compact(
            client.duplicate_page_view(
                workspace_id,
                view_id,
                suffix=suffix,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_create_page_database_view", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_create_page_database_view(
    workspace_id: str,
    view_id: str,
    layout: int,
    name: str | None = None,
    dry_run: bool = True,
) -> str:
    """Create a database view inside a page. Dry-run by default."""
    with _client() as client:
        return compact(
            client.create_page_database_view(
                workspace_id,
                view_id,
                layout=layout,
                name=name,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_trash_page_view", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_trash_page_view(workspace_id: str, view_id: str, dry_run: bool = True) -> str:
    """Move a page view to trash. Dry-run by default."""
    with _client() as client:
        return compact(client.move_page_view_to_trash(workspace_id, view_id, dry_run=dry_run))


@mcp.tool(name="appflowy_restore_page_view", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_restore_page_view(workspace_id: str, view_id: str, dry_run: bool = True) -> str:
    """Restore a page view from trash. Dry-run by default."""
    with _client() as client:
        return compact(client.restore_page_view_from_trash(workspace_id, view_id, dry_run=dry_run))


@mcp.tool(name="appflowy_delete_trashed_page_view", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_delete_trashed_page_view(
    workspace_id: str,
    view_id: str,
    dry_run: bool = True,
) -> str:
    """Permanently delete a trashed page view. Dry-run by default."""
    with _client() as client:
        return compact(client.delete_page_view_from_trash(workspace_id, view_id, dry_run=dry_run))


@mcp.tool(name="appflowy_add_recent_pages", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_add_recent_pages(
    workspace_id: str,
    recent_view_ids: list[str],
    dry_run: bool = True,
) -> str:
    """Add pages to AppFlowy's recent list. Dry-run by default."""
    with _client() as client:
        return compact(client.add_recent_pages(workspace_id, recent_view_ids, dry_run=dry_run))


@mcp.tool(name="appflowy_restore_all_pages_from_trash", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_restore_all_pages_from_trash(workspace_id: str, dry_run: bool = True) -> str:
    """Restore all trashed pages in a workspace. Dry-run by default."""
    with _client() as client:
        return compact(client.restore_all_pages_from_trash(workspace_id, dry_run=dry_run))


@mcp.tool(name="appflowy_delete_all_pages_from_trash", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_delete_all_pages_from_trash(workspace_id: str, dry_run: bool = True) -> str:
    """Permanently delete all trashed pages in a workspace. Dry-run by default."""
    with _client() as client:
        return compact(client.delete_all_pages_from_trash(workspace_id, dry_run=dry_run))


@mcp.tool(name="appflowy_list_recent_views", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_list_recent_views(workspace_id: str) -> str:
    """List recently visited views in a workspace."""
    with _client() as client:
        return compact(client.list_recent_views(workspace_id))


@mcp.tool(name="appflowy_list_favorite_views", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_list_favorite_views(workspace_id: str) -> str:
    """List favorite views in a workspace."""
    with _client() as client:
        return compact(client.list_favorite_views(workspace_id))


@mcp.tool(name="appflowy_list_trash_views", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_list_trash_views(workspace_id: str) -> str:
    """List views currently in workspace trash."""
    with _client() as client:
        return compact(client.list_trash_views(workspace_id))


@mcp.tool(name="appflowy_list_databases", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_list_databases(workspace_id: str) -> str:
    """List databases in a workspace."""
    with _client() as client:
        return compact(client.list_databases(workspace_id))


@mcp.tool(name="appflowy_get_database_schema", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_get_database_schema(workspace_id: str, database_id: str) -> str:
    """List fields/schema for a database."""
    with _client() as client:
        return compact(client.list_database_fields(workspace_id, database_id))


@mcp.tool(name="appflowy_create_database_field", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_create_database_field(
    workspace_id: str,
    database_id: str,
    name: str,
    field_type: int,
    type_option_data: dict | None = None,
    dry_run: bool = True,
) -> str:
    """Create a database field from explicit AppFlowy field-type payloads."""
    with _client() as client:
        return compact(
            client.create_database_field(
                workspace_id,
                database_id,
                name=name,
                field_type=field_type,
                type_option_data=type_option_data,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_add_select_option", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_add_select_option(
    workspace_id: str,
    database_id: str,
    name: str,
    field_name: str = "Status",
    color: str = "Purple",
    option_id: str | None = None,
    view_id: str | None = None,
    dry_run: bool = True,
) -> str:
    """Add a select option, which appears as a board column when the field groups the view."""
    with _client() as client:
        return compact(
            client.add_select_option_collab(
                workspace_id,
                database_id,
                field_name=field_name,
                name=name,
                color=color,
                option_id=option_id,
                view_id=view_id,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_rename_select_option", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_rename_select_option(
    workspace_id: str,
    database_id: str,
    new_name: str,
    field_name: str = "Status",
    option_id: str | None = None,
    option_name: str | None = None,
    dry_run: bool = True,
) -> str:
    """Rename a select option, usually a Status board column. Dry-run by default."""
    with _client() as client:
        return compact(
            client.rename_select_option_collab(
                workspace_id,
                database_id,
                field_name=field_name,
                option_id=option_id,
                option_name=option_name,
                new_name=new_name,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_hide_select_option", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_hide_select_option(
    workspace_id: str,
    database_id: str,
    field_name: str = "Status",
    option_id: str | None = None,
    option_name: str | None = None,
    view_id: str | None = None,
    dry_run: bool = True,
) -> str:
    """Hide a select option from board view groups. Dry-run by default."""
    with _client() as client:
        return compact(
            client.set_select_option_visibility_collab(
                workspace_id,
                database_id,
                field_name=field_name,
                option_id=option_id,
                option_name=option_name,
                visible=False,
                view_id=view_id,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_show_select_option", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_show_select_option(
    workspace_id: str,
    database_id: str,
    field_name: str = "Status",
    option_id: str | None = None,
    option_name: str | None = None,
    view_id: str | None = None,
    dry_run: bool = True,
) -> str:
    """Show a select option in board view groups. Dry-run by default."""
    with _client() as client:
        return compact(
            client.set_select_option_visibility_collab(
                workspace_id,
                database_id,
                field_name=field_name,
                option_id=option_id,
                option_name=option_name,
                visible=True,
                view_id=view_id,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_list_database_row_ids", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_list_database_row_ids(workspace_id: str, database_id: str) -> str:
    """List row IDs for a database."""
    with _client() as client:
        return compact(client.list_database_row_ids(workspace_id, database_id))


@mcp.tool(name="appflowy_list_updated_database_rows", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_list_updated_database_rows(
    workspace_id: str,
    database_id: str,
    after: str | None = None,
) -> str:
    """List database rows updated after an optional RFC3339 timestamp."""
    with _client() as client:
        return compact(
            client.list_updated_database_rows(
                workspace_id,
                database_id,
                after=after,
            )
        )


@mcp.tool(name="appflowy_list_quick_notes", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_list_quick_notes(
    workspace_id: str,
    search_term: str | None = None,
    offset: int | None = None,
    limit: int | None = None,
) -> str:
    """List quick notes in a workspace with optional search/pagination."""
    with _client() as client:
        return compact(
            client.list_quick_notes(
                workspace_id,
                search_term=search_term,
                offset=offset,
                limit=limit,
            )
        )


@mcp.tool(name="appflowy_create_quick_note", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_create_quick_note(
    workspace_id: str,
    data: object | None = None,
    dry_run: bool = True,
) -> str:
    """Create a quick note.

    Dry-run by default; real writes require APPFLOWY_ALLOW_WRITES=true.
    """
    with _client() as client:
        return compact(client.create_quick_note(workspace_id, data=data, dry_run=dry_run))


@mcp.tool(name="appflowy_update_quick_note", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_update_quick_note(
    workspace_id: str,
    quick_note_id: str,
    data: object,
    dry_run: bool = True,
) -> str:
    """Update a quick note's JSON data.

    Dry-run by default; real writes require APPFLOWY_ALLOW_WRITES=true.
    """
    with _client() as client:
        return compact(
            client.update_quick_note(
                workspace_id,
                quick_note_id,
                data=data,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_delete_quick_note", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_delete_quick_note(
    workspace_id: str,
    quick_note_id: str,
    dry_run: bool = True,
) -> str:
    """Delete a quick note.

    Dry-run by default; real writes require APPFLOWY_ALLOW_WRITES=true.
    """
    with _client() as client:
        return compact(client.delete_quick_note(workspace_id, quick_note_id, dry_run=dry_run))


@mcp.tool(name="appflowy_search_documents", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_search_documents(
    workspace_id: str,
    query: str,
    limit: int | None = None,
    preview_size: int | None = None,
    score: float | None = None,
) -> str:
    """Search indexed documents in a workspace.

    This calls AppFlowy's read-only GET /api/search/{workspace_id}
    endpoint. It does not call the AI summary endpoint.
    """
    with _client() as client:
        return compact(
            client.search_documents(
                workspace_id,
                query,
                limit=limit,
                preview_size=preview_size,
                score=score,
            )
        )


@mcp.tool(name="appflowy_get_database_rows", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_get_database_rows(
    workspace_id: str,
    database_id: str,
    ids: list[str],
    with_doc: bool = False,
) -> str:
    """Fetch database row details by explicit row IDs."""
    with _client() as client:
        return compact(client.get_database_rows(workspace_id, database_id, ids, with_doc=with_doc))


@mcp.tool(name="appflowy_list_select_options", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_list_select_options(
    workspace_id: str,
    database_id: str,
    field_name: str = "Status",
) -> str:
    """List options for a select-like field, typically Status."""
    with _client() as client:
        return compact(client.list_select_options(workspace_id, database_id, field_name=field_name))


@mcp.tool(name="appflowy_get_collab_json", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_get_collab_json(
    workspace_id: str,
    object_id: str,
    collab_type: str = "Database",
) -> str:
    """Fetch a collab document as raw JSON for diagnostics.

    ``collab_type`` is the string name or integer value of the collab type.
    Known names: ``Database`` (1), ``Document`` (0), ``Folder`` (3),
    ``DatabaseRow`` (4), ``WorkspaceDatabase`` (2).
    """
    with _client() as client:
        return compact(client.get_collab_json(workspace_id, object_id, collab_type=collab_type))


@mcp.tool(name="appflowy_get_database_row_orders", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_get_database_row_orders(workspace_id: str, database_id: str) -> str:
    """Return per-view row orders extracted from a database collab document.

    Each entry contains ``view_id`` and ``row_orders`` (ordered list of row-id
    strings).  Useful for inspecting board/grid card order without mutating state.
    """
    with _client() as client:
        return compact(client.get_database_row_orders(workspace_id, database_id))


@mcp.tool(name="appflowy_get_database_view_configs", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_get_database_view_configs(workspace_id: str, database_id: str) -> str:
    """Return database view configuration extracted from collab JSON.

    Each entry summarizes one AppFlowy database view: layout, layout settings,
    filters, sorts, board/group settings, field settings, field order and row
    count. This is read-only and does not mutate view configuration.
    """
    with _client() as client:
        return compact(client.get_database_view_configs(workspace_id, database_id))


@mcp.tool(name="appflowy_get_database_blob_diff", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_get_database_blob_diff(
    workspace_id: str,
    database_id: str,
    version: int = 1,
) -> str:
    """Summarise AppFlowy Web's database blob/diff response.

    This is a read-only diagnostic for the browser's row-document seed path.
    It returns row ids, operation types, RID values and doc-state byte counts,
    but never returns the raw binary document state.
    """
    with _client() as client:
        return compact(
            client.get_database_blob_diff_summary(
                workspace_id,
                database_id,
                version=version,
            )
        )


@mcp.tool(name="appflowy_list_tasks", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_list_tasks(
    workspace_id: str,
    database_id: str,
    with_doc: bool = False,
) -> str:
    """List task rows from one AppFlowy database."""
    with _client() as client:
        return compact(client.list_tasks(workspace_id, database_id, with_doc=with_doc))


@mcp.tool(name="appflowy_search_tasks", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_search_tasks(
    workspace_id: str,
    database_id: str,
    description: str,
    mode: str = "contains",
    case_sensitive: bool = False,
    with_doc: bool = False,
) -> str:
    """Search task rows by Description text with exact or contains matching."""
    with _client() as client:
        return compact(
            client.search_tasks_by_description(
                workspace_id,
                database_id,
                description,
                mode=mode,
                case_sensitive=case_sensitive,
                with_doc=with_doc,
            )
        )


@mcp.tool(name="appflowy_verify_database_row", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_verify_database_row(
    workspace_id: str,
    database_id: str,
    row_id: str,
    include_blob_diff: bool = True,
) -> str:
    """Verify one row through REST, row_orders and row collab signals.

    This is a data-plane verification. AppFlowy Web Board may still need a
    Grid/refresh warm-up before it renders the card.
    """
    with _client() as client:
        return compact(
            client.verify_database_row(
                workspace_id,
                database_id,
                row_id,
                include_blob_diff=include_blob_diff,
            )
        )


@mcp.tool(name="appflowy_create_task", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_create_task(
    workspace_id: str,
    database_id: str,
    task_key: str,
    description: str,
    status: str = "To Do",
    document: str | None = None,
    dry_run: bool = True,
    include_blob_diff: bool = True,
) -> str:
    """Create a browser-visible task row with post-write verification."""
    with _client() as client:
        return compact(
            client.create_task(
                workspace_id,
                database_id,
                task_key=task_key,
                description=description,
                status=status,
                document=document,
                dry_run=dry_run,
                include_blob_diff=include_blob_diff,
            )
        )


@mcp.tool(name="appflowy_update_task", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_update_task(
    workspace_id: str,
    database_id: str,
    task_key: str,
    description: str | None = None,
    status: str | None = None,
    document: str | None = None,
    dry_run: bool = True,
    include_blob_diff: bool = True,
) -> str:
    """Update a managed task by stable task_key and verify API/collab state."""
    with _client() as client:
        return compact(
            client.update_task(
                workspace_id,
                database_id,
                task_key=task_key,
                description=description,
                status=status,
                document=document,
                dry_run=dry_run,
                include_blob_diff=include_blob_diff,
            )
        )


@mcp.tool(name="appflowy_update_task_by_name", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_update_task_by_name(
    workspace_id: str,
    database_id: str,
    description: str,
    new_description: str | None = None,
    status: str | None = None,
    match_mode: str = "exact",
    case_sensitive: bool = False,
    dry_run: bool = True,
) -> str:
    """Update one task resolved by Description text. Ambiguous matches do not write."""
    with _client() as client:
        return compact(
            client.update_task_by_description(
                workspace_id,
                database_id,
                description,
                new_description=new_description,
                status=status,
                match_mode=match_mode,
                case_sensitive=case_sensitive,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_move_task", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_move_task(
    workspace_id: str,
    database_id: str,
    task_key: str,
    status: str,
    dry_run: bool = True,
) -> str:
    """Move a managed task to another Status option."""
    with _client() as client:
        return compact(
            client.move_task(
                workspace_id,
                database_id,
                task_key=task_key,
                status=status,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_move_task_by_name", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_move_task_by_name(
    workspace_id: str,
    database_id: str,
    description: str,
    status: str,
    match_mode: str = "exact",
    case_sensitive: bool = False,
    dry_run: bool = True,
) -> str:
    """Move one task resolved by Description text. Ambiguous matches do not write."""
    with _client() as client:
        return compact(
            client.move_task_by_description(
                workspace_id,
                database_id,
                description,
                status=status,
                match_mode=match_mode,
                case_sensitive=case_sensitive,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_update_database_row_by_id", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_update_database_row_by_id(
    workspace_id: str,
    database_id: str,
    row_id: str,
    values: dict[str, object],
    dry_run: bool = True,
) -> str:
    """Update an existing AppFlowy row by row id via DatabaseRow collab/Yjs.

    Use this for manual/UI-created rows or any row where only the row_id is
    known. For MCP-managed tasks with a stable task_key, prefer
    appflowy_update_task/appflowy_move_task.
    """
    with _client() as client:
        return compact(
            client.update_database_row_by_id_collab(
                workspace_id,
                database_id,
                row_id,
                values=values,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_move_task_by_id", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_move_task_by_id(
    workspace_id: str,
    database_id: str,
    row_id: str,
    status: str,
    dry_run: bool = True,
) -> str:
    """Move an existing/manual task row by row id via DatabaseRow collab/Yjs."""
    with _client() as client:
        return compact(
            client.move_task_by_row_id(
                workspace_id,
                database_id,
                row_id,
                status=status,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_delete_task", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_delete_task(
    workspace_id: str,
    database_id: str,
    row_id: str,
    dry_run: bool = True,
) -> str:
    """Delete a task by row id from all database views via the Yjs collab path."""
    with _client() as client:
        return compact(client.delete_task(workspace_id, database_id, row_id, dry_run=dry_run))


@mcp.tool(name="appflowy_delete_task_by_name", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_delete_task_by_name(
    workspace_id: str,
    database_id: str,
    description: str,
    match_mode: str = "exact",
    case_sensitive: bool = False,
    dry_run: bool = True,
) -> str:
    """Delete one task resolved by Description text. Ambiguous matches do not write."""
    with _client() as client:
        return compact(
            client.delete_task_by_description(
                workspace_id,
                database_id,
                description,
                match_mode=match_mode,
                case_sensitive=case_sensitive,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_create_database_row", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_create_database_row(
    workspace_id: str,
    database_id: str,
    cells: dict[str, object],
    document: str | None = None,
    dry_run: bool = True,
) -> str:
    """Create one database row.

    Dry-run by default; real writes require APPFLOWY_ALLOW_WRITES=true.
    """
    with _client() as client:
        return compact(
            client.create_database_row(
                workspace_id,
                database_id,
                cells=cells,
                document=document,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_create_verified_database_row", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_create_verified_database_row(
    workspace_id: str,
    database_id: str,
    cells: dict[str, object],
    document: str | None = None,
    dry_run: bool = True,
    include_blob_diff: bool = True,
) -> str:
    """Create one row and verify API/collab visibility after the write.

    Dry-run by default; real writes require APPFLOWY_ALLOW_WRITES=true.
    """
    with _client() as client:
        return compact(
            client.create_database_row_verified(
                workspace_id,
                database_id,
                cells=cells,
                document=document,
                dry_run=dry_run,
                include_blob_diff=include_blob_diff,
            )
        )


@mcp.tool(name="appflowy_create_typed_database_row", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_create_typed_database_row(
    workspace_id: str,
    database_id: str,
    values: dict[str, object],
    document: str | None = None,
    dry_run: bool = True,
    include_blob_diff: bool = True,
) -> str:
    """Create one row from human-friendly typed field values.

    Values are keyed by AppFlowy field name or id and normalized against the
    live database schema. Dry-run by default; real writes require
    APPFLOWY_ALLOW_WRITES=true.
    """
    with _client() as client:
        return compact(
            client.create_typed_database_row_verified(
                workspace_id,
                database_id,
                values=values,
                document=document,
                dry_run=dry_run,
                include_blob_diff=include_blob_diff,
            )
        )


@mcp.tool(name="appflowy_upsert_database_row", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_upsert_database_row(
    workspace_id: str,
    database_id: str,
    cells: dict[str, object],
    pre_hash: str | None = None,
    document: str | None = None,
    dry_run: bool = True,
) -> str:
    """Upsert one database row.

    Dry-run by default; real writes require APPFLOWY_ALLOW_WRITES=true.
    """
    with _client() as client:
        return compact(
            client.upsert_database_row(
                workspace_id,
                database_id,
                pre_hash=pre_hash,
                cells=cells,
                document=document,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_upsert_typed_database_row", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_upsert_typed_database_row(
    workspace_id: str,
    database_id: str,
    values: dict[str, object],
    pre_hash: str | None = None,
    document: str | None = None,
    dry_run: bool = True,
) -> str:
    """Upsert one row from human-friendly typed field values.

    Values are keyed by AppFlowy field name or id and normalized against the
    live database schema. Dry-run by default; real writes require
    APPFLOWY_ALLOW_WRITES=true.
    """
    with _client() as client:
        return compact(
            client.upsert_typed_database_row(
                workspace_id,
                database_id,
                pre_hash=pre_hash,
                values=values,
                document=document,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_upsert_managed_task", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_upsert_managed_task(
    workspace_id: str,
    database_id: str,
    task_key: str,
    description: str | None = None,
    status: str | None = None,
    document: str | None = None,
    dry_run: bool = True,
) -> str:
    """Advanced idempotent task_key/pre_hash upsert.

    For user-visible task/card creation, prefer appflowy_create_task; fresh
    pre_hash upserts may verify through the data plane before AppFlowy Web Grid
    renders them.
    """
    with _client() as client:
        return compact(
            client.upsert_managed_task(
                workspace_id,
                database_id,
                task_key=task_key,
                description=description,
                status=status,
                document=document,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_upsert_verified_managed_task", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_upsert_verified_managed_task(
    workspace_id: str,
    database_id: str,
    task_key: str,
    description: str | None = None,
    status: str | None = None,
    document: str | None = None,
    dry_run: bool = True,
    include_blob_diff: bool = True,
) -> str:
    """Advanced idempotent task_key/pre_hash upsert with data-plane verification.

    For user-visible task/card creation, prefer appflowy_create_task; data-plane
    verification does not by itself prove AppFlowy Web Grid rendering.
    """
    with _client() as client:
        return compact(
            client.upsert_managed_task_verified(
                workspace_id,
                database_id,
                task_key=task_key,
                description=description,
                status=status,
                document=document,
                dry_run=dry_run,
                include_blob_diff=include_blob_diff,
            )
        )


@mcp.tool(name="appflowy_move_managed_task_status", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_move_managed_task_status(
    workspace_id: str,
    database_id: str,
    task_key: str,
    status: str,
    dry_run: bool = True,
) -> str:
    """Move an MCP-managed task to another Status option, verified after execution."""
    with _client() as client:
        return compact(
            client.move_managed_task_status(
                workspace_id,
                database_id,
                task_key=task_key,
                status=status,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_delete_database_row", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_delete_database_row(
    workspace_id: str,
    database_id: str,
    row_id: str,
    dry_run: bool = True,
) -> str:
    """[EXPERIMENTAL] Delete a database row via Yjs collab mutation.

    This is the only confirmed-correct delete path for AppFlowy board cards.
    AppFlowy does not expose a REST row-delete endpoint; deletion requires
    a Yjs collab update posted to the ``web-update`` endpoint.

    **Requires Node.js 18+ and the ``yjs`` npm package** in
    ``src/appflowy_mcp_toolkit/collab/node_modules/``. Run
    ``cd src/appflowy_mcp_toolkit/collab && npm install`` once.

    Dry-run by default. Real writes require ``APPFLOWY_ALLOW_WRITES=true``
    **and** ``APPFLOWY_ALLOW_COLLAB_WRITES=true`` in the environment.

    The row must be present in the binary collab state (not just the REST
    row list). Rows freshly created via REST may not yet appear in the
    binary collab due to sync lag; check ``row_found`` in the response.
    """
    with _client() as client:
        return compact(
            client.delete_database_row_collab(
                workspace_id,
                database_id,
                row_id,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_reorder_database_row", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_reorder_database_row(
    workspace_id: str,
    database_id: str,
    view_id: str,
    row_id: str,
    before_row_id: str | None = None,
    dry_run: bool = True,
) -> str:
    """Reorder a row/card inside a board or grid view.

    Moves ``row_id`` immediately before ``before_row_id`` in ``view_id``.
    Pass ``before_row_id=None`` (or omit it) to move the row to the end.

    Dry-run by default. Real writes require APPFLOWY_ALLOW_WRITES=true
    and APPFLOWY_ALLOW_COLLAB_WRITES=true.

    Use ``appflowy_get_database_row_orders`` to inspect current row order
    before calling this tool.
    """
    with _client() as client:
        return compact(
            client.reorder_database_row_collab(
                workspace_id,
                database_id,
                view_id,
                row_id,
                before_row_id=before_row_id,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_reorder_database_column", annotations={"readOnlyHint": False})  # type: ignore[arg-type]
def appflowy_reorder_database_column(
    workspace_id: str,
    database_id: str,
    view_id: str,
    field_id: str,
    group_id: str,
    before_group_id: str | None = None,
    dry_run: bool = True,
) -> str:
    """Reorder a board column (status group) inside a database view.

    Moves the column identified by ``group_id`` (the Status option id)
    immediately before ``before_group_id``.  Pass ``before_group_id=None``
    (or omit it) to move the column to the end.

    ``field_id`` is the grouping field id (e.g. the Status field id);
    obtain it from ``appflowy_list_database_fields``.
    ``group_id`` is the select option id for the column;
    obtain it from ``appflowy_get_database_view_configs``.

    Dry-run by default. Real writes require APPFLOWY_ALLOW_WRITES=true
    and APPFLOWY_ALLOW_COLLAB_WRITES=true.
    """
    with _client() as client:
        return compact(
            client.reorder_database_column_collab(
                workspace_id,
                database_id,
                view_id,
                field_id,
                group_id,
                before_group_id=before_group_id,
                dry_run=dry_run,
            )
        )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
