from __future__ import annotations

from mcp.types import ToolAnnotations

from appflowy_mcp_toolkit.formatting import compact
from appflowy_mcp_toolkit.mcp.server import _client, mcp


@mcp.tool(name="appflowy_get_folder", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_get_folder(
    workspace_id: str,
    depth: int | None = None,
    root_view_id: str | None = None,
) -> str:
    """Get a workspace folder/view tree or subtree."""
    with _client() as client:
        return compact(client.get_folder(workspace_id, depth=depth, root_view_id=root_view_id))


@mcp.tool(
    name="appflowy_create_folder_view",
    annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=True),
)
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


@mcp.tool(name="appflowy_get_page_view", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_get_page_view(workspace_id: str, view_id: str) -> str:
    """Get a page/view collab payload by view id."""
    with _client() as client:
        return compact(client.get_page_view(workspace_id, view_id))


@mcp.tool(
    name="appflowy_create_page_view",
    annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=True),
)
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


@mcp.tool(name="appflowy_update_page_view", annotations=ToolAnnotations(readOnlyHint=False))
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


@mcp.tool(name="appflowy_rename_page_view", annotations=ToolAnnotations(readOnlyHint=False))
def appflowy_rename_page_view(
    workspace_id: str,
    view_id: str,
    name: str,
    dry_run: bool = True,
) -> str:
    """Rename a page view. Dry-run by default."""
    with _client() as client:
        return compact(client.update_page_name(workspace_id, view_id, name=name, dry_run=dry_run))


@mcp.tool(name="appflowy_favorite_page_view", annotations=ToolAnnotations(readOnlyHint=False))
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


@mcp.tool(name="appflowy_remove_page_icon", annotations=ToolAnnotations(readOnlyHint=False))
def appflowy_remove_page_icon(workspace_id: str, view_id: str, dry_run: bool = True) -> str:
    """Remove a page icon. Dry-run by default."""
    with _client() as client:
        return compact(client.remove_page_icon(workspace_id, view_id, dry_run=dry_run))


@mcp.tool(name="appflowy_append_blocks_to_page", annotations=ToolAnnotations(readOnlyHint=False))
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


@mcp.tool(name="appflowy_append_markdown_to_page", annotations=ToolAnnotations(readOnlyHint=False))
def appflowy_append_markdown_to_page(
    workspace_id: str,
    view_id: str,
    markdown: str,
    dry_run: bool = True,
) -> str:
    """Convert Markdown to AppFlowy blocks and append to a page.

    Supports: paragraphs, # through ###### headings, - / * / + unordered
    lists, N. ordered lists, > blockquotes.  Inline rich formatting is
    kept as plain text; full inline conversion is backlog.
    Dry-run by default.  Live execution requires APPFLOWY_ALLOW_WRITES=true.
    Does NOT fetch, replace, or edit existing page content.
    """
    with _client() as client:
        return compact(
            client.append_markdown_to_page(
                workspace_id,
                view_id,
                markdown=markdown,
                dry_run=dry_run,
            )
        )


@mcp.tool(name="appflowy_move_page_view", annotations=ToolAnnotations(readOnlyHint=False))
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


@mcp.tool(
    name="appflowy_reorder_favorite_page_view", annotations=ToolAnnotations(readOnlyHint=False)
)
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


@mcp.tool(name="appflowy_duplicate_page_view", annotations=ToolAnnotations(readOnlyHint=False))
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


@mcp.tool(
    name="appflowy_create_page_database_view", annotations=ToolAnnotations(readOnlyHint=False)
)
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


@mcp.tool(
    name="appflowy_trash_page_view",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)
def appflowy_trash_page_view(workspace_id: str, view_id: str, dry_run: bool = True) -> str:
    """Move a page view to trash. Dry-run by default."""
    with _client() as client:
        return compact(client.move_page_view_to_trash(workspace_id, view_id, dry_run=dry_run))


@mcp.tool(name="appflowy_restore_page_view", annotations=ToolAnnotations(readOnlyHint=False))
def appflowy_restore_page_view(workspace_id: str, view_id: str, dry_run: bool = True) -> str:
    """Restore a page view from trash. Dry-run by default."""
    with _client() as client:
        return compact(client.restore_page_view_from_trash(workspace_id, view_id, dry_run=dry_run))


@mcp.tool(
    name="appflowy_delete_trashed_page_view",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)
def appflowy_delete_trashed_page_view(
    workspace_id: str,
    view_id: str,
    dry_run: bool = True,
) -> str:
    """Permanently delete a trashed page view. Dry-run by default."""
    with _client() as client:
        return compact(client.delete_page_view_from_trash(workspace_id, view_id, dry_run=dry_run))


@mcp.tool(name="appflowy_add_recent_pages", annotations=ToolAnnotations(readOnlyHint=False))
def appflowy_add_recent_pages(
    workspace_id: str,
    recent_view_ids: list[str],
    dry_run: bool = True,
) -> str:
    """Add pages to AppFlowy's recent list. Dry-run by default."""
    with _client() as client:
        return compact(client.add_recent_pages(workspace_id, recent_view_ids, dry_run=dry_run))


@mcp.tool(
    name="appflowy_restore_all_pages_from_trash", annotations=ToolAnnotations(readOnlyHint=False)
)
def appflowy_restore_all_pages_from_trash(workspace_id: str, dry_run: bool = True) -> str:
    """Restore all trashed pages in a workspace. Dry-run by default."""
    with _client() as client:
        return compact(client.restore_all_pages_from_trash(workspace_id, dry_run=dry_run))


@mcp.tool(
    name="appflowy_delete_all_pages_from_trash",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)
def appflowy_delete_all_pages_from_trash(workspace_id: str, dry_run: bool = True) -> str:
    """Permanently delete all trashed pages in a workspace. Dry-run by default."""
    with _client() as client:
        return compact(client.delete_all_pages_from_trash(workspace_id, dry_run=dry_run))


@mcp.tool(name="appflowy_list_recent_views", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_list_recent_views(workspace_id: str) -> str:
    """List recently visited views in a workspace."""
    with _client() as client:
        return compact(client.list_recent_views(workspace_id))


@mcp.tool(name="appflowy_list_favorite_views", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_list_favorite_views(workspace_id: str) -> str:
    """List favorite views in a workspace."""
    with _client() as client:
        return compact(client.list_favorite_views(workspace_id))


@mcp.tool(name="appflowy_list_trash_views", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_list_trash_views(workspace_id: str) -> str:
    """List views currently in workspace trash."""
    with _client() as client:
        return compact(client.list_trash_views(workspace_id))
