from __future__ import annotations

from mcp.types import ToolAnnotations

from appflowy_mcp_toolkit.formatting import compact
from appflowy_mcp_toolkit.mcp.server import StructuredToolResult, _client, _structured, mcp


@mcp.tool(name="appflowy_list_template_categories", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_list_template_categories(
    name_contains: str | None = None,
    category_type: int | None = None,
) -> str:
    """List AppFlowy template-center categories."""
    with _client() as client:
        return compact(
            client.list_template_categories(
                name_contains=name_contains,
                category_type=category_type,
            )
        )


@mcp.tool(name="appflowy_get_template_category", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_get_template_category(category_id: str) -> str:
    """Get one AppFlowy template category by id."""
    with _client() as client:
        return compact(client.get_template_category(category_id))


@mcp.tool(name="appflowy_list_template_creators", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_list_template_creators(name_contains: str | None = None) -> str:
    """List AppFlowy template-center creators."""
    with _client() as client:
        return compact(client.list_template_creators(name_contains=name_contains))


@mcp.tool(name="appflowy_get_template_creator", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_get_template_creator(creator_id: str) -> str:
    """Get one AppFlowy template creator by id."""
    with _client() as client:
        return compact(client.get_template_creator(creator_id))


@mcp.tool(name="appflowy_list_templates", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_list_templates(
    category_id: str | None = None,
    is_featured: bool | None = None,
    is_new_template: bool | None = None,
    name_contains: str | None = None,
) -> StructuredToolResult:
    """List AppFlowy templates with publish metadata when provided by AppFlowy."""
    with _client() as client:
        return _structured(
            client.list_templates(
                category_id=category_id,
                is_featured=is_featured,
                is_new_template=is_new_template,
                name_contains=name_contains,
            )
        )


@mcp.tool(name="appflowy_get_template", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_get_template(view_id: str) -> str:
    """Get one AppFlowy template by template view id."""
    with _client() as client:
        return compact(client.get_template(view_id))


@mcp.tool(name="appflowy_get_template_homepage", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_get_template_homepage(per_count: int | None = None) -> str:
    """Get AppFlowy's template-center homepage groups."""
    with _client() as client:
        return compact(client.get_template_homepage(per_count=per_count))
