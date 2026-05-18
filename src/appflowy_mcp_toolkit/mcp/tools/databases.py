from __future__ import annotations

from mcp.types import ToolAnnotations

from appflowy_mcp_toolkit.formatting import compact
from appflowy_mcp_toolkit.mcp.server import StructuredToolResult, _client, _structured, mcp


@mcp.tool(
    name="appflowy_list_databases",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
def appflowy_list_databases(workspace_id: str) -> str:
    """List databases in a workspace."""
    with _client() as client:
        return compact(client.list_databases(workspace_id))


@mcp.tool(name="appflowy_get_database_schema", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_get_database_schema(workspace_id: str, database_id: str) -> str:
    """List fields/schema for a database."""
    with _client() as client:
        return compact(client.list_database_fields(workspace_id, database_id))


@mcp.tool(name="appflowy_create_database_field", annotations=ToolAnnotations(readOnlyHint=False))
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


@mcp.tool(name="appflowy_add_select_option", annotations=ToolAnnotations(readOnlyHint=False))
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


@mcp.tool(name="appflowy_rename_select_option", annotations=ToolAnnotations(readOnlyHint=False))
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


@mcp.tool(name="appflowy_hide_select_option", annotations=ToolAnnotations(readOnlyHint=False))
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


@mcp.tool(name="appflowy_show_select_option", annotations=ToolAnnotations(readOnlyHint=False))
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


@mcp.tool(name="appflowy_list_database_row_ids", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_list_database_row_ids(workspace_id: str, database_id: str) -> str:
    """List row IDs for a database."""
    with _client() as client:
        return compact(client.list_database_row_ids(workspace_id, database_id))


@mcp.tool(
    name="appflowy_list_updated_database_rows", annotations=ToolAnnotations(readOnlyHint=True)
)
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


@mcp.tool(name="appflowy_list_quick_notes", annotations=ToolAnnotations(readOnlyHint=True))
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


@mcp.tool(
    name="appflowy_create_quick_note",
    annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=True),
)
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


@mcp.tool(name="appflowy_update_quick_note", annotations=ToolAnnotations(readOnlyHint=False))
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


@mcp.tool(
    name="appflowy_delete_quick_note",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)
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


@mcp.tool(name="appflowy_search_documents", annotations=ToolAnnotations(readOnlyHint=True))
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


@mcp.tool(
    name="appflowy_get_database_rows",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
def appflowy_get_database_rows(
    workspace_id: str,
    database_id: str,
    ids: list[str],
    with_doc: bool = False,
) -> StructuredToolResult:
    """Fetch database row details by explicit row IDs."""
    with _client() as client:
        return _structured(
            client.get_database_rows(workspace_id, database_id, ids, with_doc=with_doc)
        )


@mcp.tool(name="appflowy_list_select_options", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_list_select_options(
    workspace_id: str,
    database_id: str,
    field_name: str = "Status",
) -> str:
    """List options for a select-like field, typically Status."""
    with _client() as client:
        return compact(client.list_select_options(workspace_id, database_id, field_name=field_name))
