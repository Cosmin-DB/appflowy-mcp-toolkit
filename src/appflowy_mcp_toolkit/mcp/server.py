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


@mcp.tool(name="appflowy_get_folder", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_get_folder(
    workspace_id: str,
    depth: int | None = None,
    root_view_id: str | None = None,
) -> str:
    """Get a workspace folder/view tree or subtree."""
    with _client() as client:
        return compact(client.get_folder(workspace_id, depth=depth, root_view_id=root_view_id))


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


@mcp.tool(name="appflowy_list_database_row_ids", annotations={"readOnlyHint": True})  # type: ignore[arg-type]
def appflowy_list_database_row_ids(workspace_id: str, database_id: str) -> str:
    """List row IDs for a database."""
    with _client() as client:
        return compact(client.list_database_row_ids(workspace_id, database_id))


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
    """Create/update an MCP-managed task using a stable task_key/pre_hash."""
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


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
