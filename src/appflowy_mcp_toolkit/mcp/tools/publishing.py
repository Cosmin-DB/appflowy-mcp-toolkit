from __future__ import annotations

from mcp.types import ToolAnnotations

from appflowy_mcp_toolkit.formatting import compact
from appflowy_mcp_toolkit.mcp.server import StructuredToolResult, _client, _structured, mcp


@mcp.tool(name="appflowy_get_publish_namespace", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_get_publish_namespace(workspace_id: str) -> str:
    """Get the public publish namespace for one AppFlowy workspace."""
    with _client() as client:
        return compact(client.get_workspace_publish_namespace(workspace_id))


@mcp.tool(name="appflowy_get_publish_default", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_get_publish_default(workspace_id: str) -> str:
    """Get the default published view info for one AppFlowy workspace."""
    with _client() as client:
        return compact(client.get_workspace_publish_default(workspace_id))


@mcp.tool(
    name="appflowy_list_published_pages",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
def appflowy_list_published_pages(workspace_id: str) -> str:
    """List published page metadata for one AppFlowy workspace."""
    with _client() as client:
        return compact(client.list_published_pages(workspace_id))


@mcp.tool(name="appflowy_get_published_page_info", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_get_published_page_info(
    view_id: str,
    include_unpublished: bool = False,
) -> str:
    """Get published page metadata for one AppFlowy view id."""
    with _client() as client:
        return compact(
            client.get_published_page_info(
                view_id,
                include_unpublished=include_unpublished,
            )
        )


@mcp.tool(
    name="appflowy_publish_page",
    annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=True),
)
def appflowy_publish_page(
    workspace_id: str,
    view_id: str,
    publish_name: str | None = None,
    visible_database_view_ids: list[str] | None = None,
    comments_enabled: bool | None = None,
    duplicate_enabled: bool | None = None,
    dry_run: bool = True,
) -> StructuredToolResult:
    """Publish an AppFlowy page view.

    Dry-run by default.  Live execution requires both
    APPFLOWY_ALLOW_WRITES=true and APPFLOWY_ALLOW_PUBLISH_WRITES=true.
    """
    with _client() as client:
        return _structured(
            client.publish_page(
                workspace_id,
                view_id,
                publish_name=publish_name,
                visible_database_view_ids=visible_database_view_ids,
                comments_enabled=comments_enabled,
                duplicate_enabled=duplicate_enabled,
                dry_run=dry_run,
            )
        )


@mcp.tool(
    name="appflowy_unpublish_page",
    annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=True, destructiveHint=True),
)
def appflowy_unpublish_page(
    workspace_id: str,
    view_id: str,
    dry_run: bool = True,
) -> str:
    """Unpublish an AppFlowy page view.

    Dry-run by default.  Live execution requires both
    APPFLOWY_ALLOW_WRITES=true and APPFLOWY_ALLOW_PUBLISH_WRITES=true.
    """
    with _client() as client:
        return compact(client.unpublish_page(workspace_id, view_id, dry_run=dry_run))


@mcp.tool(
    name="appflowy_duplicate_published_page",
    annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=True),
)
def appflowy_duplicate_published_page(
    workspace_id: str,
    published_view_id: str,
    dest_view_id: str,
    dry_run: bool = True,
) -> str:
    """Duplicate a published AppFlowy page or template into a destination view.

    Dry-run by default.  Live execution requires APPFLOWY_ALLOW_WRITES=true.
    Only works for pages/templates that are already published on AppFlowy;
    arbitrary unpublished templates cannot be instantiated via this route.
    Returns { view_id } of the duplicated root view on success.
    """
    with _client() as client:
        return compact(
            client.duplicate_published_page(
                workspace_id,
                published_view_id=published_view_id,
                dest_view_id=dest_view_id,
                dry_run=dry_run,
            )
        )


@mcp.tool(
    name="appflowy_instantiate_template",
    annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=True),
)
def appflowy_instantiate_template(
    workspace_id: str,
    template_view_id: str,
    dest_view_id: str,
    dry_run: bool = True,
) -> str:
    """Instantiate a published AppFlowy template into a destination view.

    Friendly alias for appflowy_duplicate_published_page that accepts a
    template_view_id.  Only works for pages/templates already published on
    AppFlowy.  Arbitrary unpublished templates are not supported.
    Dry-run by default.  Live execution requires APPFLOWY_ALLOW_WRITES=true.
    """
    with _client() as client:
        return compact(
            client.instantiate_template(
                workspace_id,
                template_view_id=template_view_id,
                dest_view_id=dest_view_id,
                dry_run=dry_run,
            )
        )
