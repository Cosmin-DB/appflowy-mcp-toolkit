from __future__ import annotations

from typing import Any

from appflowy_mcp_toolkit.client_parts.base import ClientCore
from appflowy_mcp_toolkit.errors import AppFlowySchemaError


class WorkspaceMixin(ClientCore):
    def list_workspaces(
        self, *, include_member_count: bool = False, include_role: bool = False
    ) -> list[dict[str, Any]]:
        data = self.request(
            "GET",
            "/api/workspace",
            params={"include_member_count": include_member_count, "include_role": include_role},
        )
        return self._extract_list(data)

    def get_server_info(self) -> dict[str, Any]:
        data = self.request("GET", "/api/server", require_auth=False)
        server_info = self._extract_data(data)
        if not isinstance(server_info, dict):
            raise AppFlowySchemaError("Expected AppFlowy server info response", payload=data)
        return server_info

    def get_user_profile(self) -> dict[str, Any]:
        data = self.request("GET", "/api/user/profile")
        profile = self._extract_data(data)
        if not isinstance(profile, dict):
            raise AppFlowySchemaError("Expected AppFlowy user profile response", payload=data)
        return profile

    def get_user_workspace_info(self) -> dict[str, Any]:
        data = self.request("GET", "/api/user/workspace")
        info = self._extract_data(data)
        if not isinstance(info, dict):
            raise AppFlowySchemaError("Expected AppFlowy user workspace response", payload=data)
        return info

    def get_workspace_settings(self, workspace_id: str) -> dict[str, Any]:
        data = self.request("GET", f"/api/workspace/{workspace_id}/settings")
        settings = self._extract_data(data)
        if not isinstance(settings, dict):
            raise AppFlowySchemaError("Expected AppFlowy workspace settings response", payload=data)
        return settings

    def list_workspace_members(self, workspace_id: str) -> list[dict[str, Any]]:
        data = self.request("GET", f"/api/workspace/{workspace_id}/member")
        return self._extract_list(data)

    def get_workspace_usage(self, workspace_id: str) -> dict[str, Any]:
        data = self.request("GET", f"/api/workspace/{workspace_id}/usage")
        usage = self._extract_data(data)
        if not isinstance(usage, dict):
            raise AppFlowySchemaError("Expected AppFlowy workspace usage response", payload=data)
        return usage

    def create_workspace(self, name: str, *, dry_run: bool = True) -> dict[str, Any]:
        payload = {"workspace_name": name}
        if dry_run:
            return {"dry_run": True, "method": "POST", "path": "/api/workspace", "json": payload}
        self._require_writes_enabled()
        return self.request("POST", "/api/workspace", json=payload)

    def create_space(
        self,
        workspace_id: str,
        *,
        name: str,
        space_permission: int = 0,
        space_icon: str = "",
        space_icon_color: str = "",
        view_id: str | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "space_permission": space_permission,
            "name": name,
            "space_icon": space_icon,
            "space_icon_color": space_icon_color,
        }
        if view_id is not None:
            payload["view_id"] = view_id
        path = f"/api/workspace/{workspace_id}/space"
        if dry_run:
            return {"dry_run": True, "method": "POST", "path": path, "json": payload}
        self._require_writes_enabled()
        return self.request("POST", path, json=payload)

    def update_space(
        self,
        workspace_id: str,
        view_id: str,
        *,
        name: str,
        space_permission: int = 0,
        space_icon: str = "",
        space_icon_color: str = "",
        dry_run: bool = True,
    ) -> dict[str, Any]:
        payload = {
            "space_permission": space_permission,
            "name": name,
            "space_icon": space_icon,
            "space_icon_color": space_icon_color,
        }
        path = f"/api/workspace/{workspace_id}/space/{view_id}"
        if dry_run:
            return {"dry_run": True, "method": "PATCH", "path": path, "json": payload}
        self._require_writes_enabled()
        return self.request("PATCH", path, json=payload)
