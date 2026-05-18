from __future__ import annotations

from mcp.types import ToolAnnotations

from appflowy_mcp_toolkit.formatting import compact
from appflowy_mcp_toolkit.mcp.server import _client, mcp
from appflowy_mcp_toolkit.workflows import safe_workflows


@mcp.tool(name="appflowy_safe_workflows", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_safe_workflows() -> str:
    """Return safe operating paths for agents using AppFlowy task/database tools."""
    return compact(safe_workflows())


@mcp.tool(
    name="appflowy_health_check",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
def appflowy_health_check() -> str:
    """Check whether AppFlowy is reachable with the configured token."""
    with _client() as client:
        return compact(client.health_check())


@mcp.tool(
    name="appflowy_list_workspaces",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
def appflowy_list_workspaces(include_member_count: bool = False, include_role: bool = False) -> str:
    """List AppFlowy workspaces visible to the configured account."""
    with _client() as client:
        data = client.list_workspaces(
            include_member_count=include_member_count,
            include_role=include_role,
        )
        return compact(data)


@mcp.tool(
    name="appflowy_get_server_info",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
def appflowy_get_server_info() -> str:
    """Get public AppFlowy server capability information."""
    with _client() as client:
        return compact(client.get_server_info())


@mcp.tool(
    name="appflowy_get_user_profile",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
def appflowy_get_user_profile() -> str:
    """Get the authenticated AppFlowy user profile."""
    with _client() as client:
        return compact(client.get_user_profile())


@mcp.tool(name="appflowy_get_user_workspace_info", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_get_user_workspace_info() -> str:
    """Get workspace metadata for the authenticated AppFlowy user."""
    with _client() as client:
        return compact(client.get_user_workspace_info())


@mcp.tool(name="appflowy_get_workspace_settings", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_get_workspace_settings(workspace_id: str) -> str:
    """Get read-only settings for one AppFlowy workspace."""
    with _client() as client:
        return compact(client.get_workspace_settings(workspace_id))


@mcp.tool(name="appflowy_list_workspace_members", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_list_workspace_members(workspace_id: str) -> str:
    """List members for one AppFlowy workspace."""
    with _client() as client:
        return compact(client.list_workspace_members(workspace_id))


@mcp.tool(name="appflowy_get_workspace_usage", annotations=ToolAnnotations(readOnlyHint=True))
def appflowy_get_workspace_usage(workspace_id: str) -> str:
    """Get read-only usage information for one AppFlowy workspace."""
    with _client() as client:
        return compact(client.get_workspace_usage(workspace_id))
