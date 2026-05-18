from __future__ import annotations

from mcp.types import ToolAnnotations

from appflowy_mcp_toolkit.formatting import compact
from appflowy_mcp_toolkit.mcp.server import StructuredToolResult, _client, _structured, mcp


@mcp.tool(name="appflowy_get_collab_json", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_get_collab_json(
    workspace_id: str,
    object_id: str,
    collab_type: str = "Database",
    summary_only: bool = True,
    include_raw: bool = False,
) -> str:
    """Fetch a collab document for diagnostics.

    **Safe defaults**: returns a compact summary (top-level keys, counts,
    metadata) without the raw collab body.  Full raw output requires
    ``include_raw=True`` and ``summary_only=False``.

    Raw collab JSON may contain large internal Yjs state and should be
    treated as diagnostic-only data.  Do not parse it as user-facing
    application data.

    ``collab_type`` string names: ``Database`` (1), ``Document`` (0),
    ``Folder`` (3), ``DatabaseRow`` (4), ``WorkspaceDatabase`` (2).
    """
    with _client() as client:
        return compact(
            client.get_collab_json(
                workspace_id,
                object_id,
                collab_type=collab_type,
                summary_only=summary_only,
                include_raw=include_raw,
            )
        )


@mcp.tool(name="appflowy_get_database_row_orders", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_get_database_row_orders(workspace_id: str, database_id: str) -> str:
    """Return per-view row orders extracted from a database collab document.

    Each entry contains ``view_id`` and ``row_orders`` (ordered list of row-id
    strings).  Useful for inspecting board/grid card order without mutating state.
    """
    with _client() as client:
        return compact(client.get_database_row_orders(workspace_id, database_id))


@mcp.tool(name="appflowy_get_database_view_configs", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_get_database_view_configs(workspace_id: str, database_id: str) -> StructuredToolResult:
    """Return database view configuration extracted from collab JSON.

    Each entry summarizes one AppFlowy database view: layout, layout settings,
    filters, sorts, board/group settings, field settings, field order and row
    count. This is read-only and does not mutate view configuration.
    """
    with _client() as client:
        return _structured(client.get_database_view_configs(workspace_id, database_id))


@mcp.tool(name="appflowy_get_database_blob_diff", annotations=ToolAnnotations(readOnlyHint=True))
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
