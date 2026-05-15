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


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
