from __future__ import annotations

from mcp.types import ToolAnnotations

from appflowy_mcp_toolkit.formatting import compact
from appflowy_mcp_toolkit.mcp.server import StructuredToolResult, _client, _structured, mcp


@mcp.tool(
    name="appflowy_list_tasks", annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True)
)
def appflowy_list_tasks(
    workspace_id: str,
    database_id: str,
    with_doc: bool = False,
) -> StructuredToolResult:
    """List task rows from one AppFlowy database."""
    with _client() as client:
        return _structured(client.list_tasks(workspace_id, database_id, with_doc=with_doc))


@mcp.tool(
    name="appflowy_search_tasks",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
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


@mcp.tool(
    name="appflowy_verify_database_row",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
def appflowy_verify_database_row(
    workspace_id: str,
    database_id: str,
    row_id: str,
    include_blob_diff: bool = True,
) -> StructuredToolResult:
    """Verify one row through REST, row_orders and row collab signals.

    This is a data-plane verification. AppFlowy Web Board may still need a
    Grid/refresh warm-up before it renders the card.
    """
    with _client() as client:
        return _structured(
            client.verify_database_row(
                workspace_id,
                database_id,
                row_id,
                include_blob_diff=include_blob_diff,
            )
        )


@mcp.tool(
    name="appflowy_create_task", annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=True)
)
def appflowy_create_task(
    workspace_id: str,
    database_id: str,
    task_key: str,
    description: str,
    status: str = "To Do",
    document: str | None = None,
    dry_run: bool = True,
    include_blob_diff: bool = True,
) -> StructuredToolResult:
    """Create a browser-visible task row with post-write verification."""
    with _client() as client:
        return _structured(
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


@mcp.tool(name="appflowy_update_task", annotations=ToolAnnotations(readOnlyHint=False))
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


@mcp.tool(name="appflowy_update_task_by_name", annotations=ToolAnnotations(readOnlyHint=False))
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


@mcp.tool(name="appflowy_move_task", annotations=ToolAnnotations(readOnlyHint=False))
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


@mcp.tool(name="appflowy_move_task_by_name", annotations=ToolAnnotations(readOnlyHint=False))
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


@mcp.tool(
    name="appflowy_update_database_row_by_id", annotations=ToolAnnotations(readOnlyHint=False)
)
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


@mcp.tool(name="appflowy_move_task_by_id", annotations=ToolAnnotations(readOnlyHint=False))
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


@mcp.tool(
    name="appflowy_delete_task",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)
def appflowy_delete_task(
    workspace_id: str,
    database_id: str,
    row_id: str,
    dry_run: bool = True,
) -> str:
    """Delete a task by row id from all database views via the Yjs collab path."""
    with _client() as client:
        return compact(client.delete_task(workspace_id, database_id, row_id, dry_run=dry_run))


@mcp.tool(
    name="appflowy_delete_task_by_name",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)
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


@mcp.tool(
    name="appflowy_create_database_row",
    annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=True),
)
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


@mcp.tool(
    name="appflowy_create_verified_database_row",
    annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=True),
)
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


@mcp.tool(
    name="appflowy_create_typed_database_row",
    annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=True),
)
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


@mcp.tool(name="appflowy_upsert_database_row", annotations=ToolAnnotations(readOnlyHint=False))
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


@mcp.tool(
    name="appflowy_upsert_typed_database_row", annotations=ToolAnnotations(readOnlyHint=False)
)
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


@mcp.tool(name="appflowy_upsert_managed_task", annotations=ToolAnnotations(readOnlyHint=False))
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


@mcp.tool(
    name="appflowy_upsert_verified_managed_task", annotations=ToolAnnotations(readOnlyHint=False)
)
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


@mcp.tool(name="appflowy_move_managed_task_status", annotations=ToolAnnotations(readOnlyHint=False))
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


@mcp.tool(
    name="appflowy_delete_database_row",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)
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


@mcp.tool(name="appflowy_reorder_database_row", annotations=ToolAnnotations(readOnlyHint=False))
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


@mcp.tool(name="appflowy_reorder_database_column", annotations=ToolAnnotations(readOnlyHint=False))
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
