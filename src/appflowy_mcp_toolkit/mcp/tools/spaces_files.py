from __future__ import annotations

from mcp.types import ToolAnnotations

from appflowy_mcp_toolkit.formatting import compact
from appflowy_mcp_toolkit.mcp.server import _client, mcp


@mcp.tool(
    name="appflowy_create_space",
    annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=True),
)
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


@mcp.tool(name="appflowy_update_space", annotations=ToolAnnotations(readOnlyHint=False))
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


@mcp.tool(name="appflowy_get_file_storage_usage", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_get_file_storage_usage(workspace_id: str) -> str:
    """Get read-only file-storage capacity usage for one workspace."""
    with _client() as client:
        return compact(client.get_file_storage_usage(workspace_id))


@mcp.tool(name="appflowy_list_file_storage_blobs", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_list_file_storage_blobs(workspace_id: str) -> str:
    """List file-storage blob metadata for one workspace without fetching blob bytes."""
    with _client() as client:
        return compact(client.list_file_storage_blobs(workspace_id))


@mcp.tool(name="appflowy_get_file_metadata", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_get_file_metadata(workspace_id: str, file_id: str) -> str:
    """Get v0 file metadata by file id without downloading blob content."""
    with _client() as client:
        return compact(client.get_file_metadata(workspace_id, file_id))


@mcp.tool(name="appflowy_get_file_metadata_v1", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_get_file_metadata_v1(workspace_id: str, parent_dir: str, file_id: str) -> str:
    """Get v1 file metadata by parent directory and file id without blob content."""
    with _client() as client:
        return compact(client.get_file_metadata_v1(workspace_id, parent_dir, file_id))


@mcp.tool(
    name="appflowy_upload_file_blob_v1",
    annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=True),
)
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


@mcp.tool(
    name="appflowy_delete_file_blob_v1",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)
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


@mcp.tool(
    name="appflowy_upload_file_as_media",
    annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=True),
)
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
