from __future__ import annotations

from typing import Any

from appflowy_mcp_toolkit.client import AppFlowyClient


class WorkspacesService:
    def __init__(self, client: AppFlowyClient):
        self.client = client

    def list(
        self, *, include_member_count: bool = False, include_role: bool = False
    ) -> list[dict[str, Any]]:
        return self.client.list_workspaces(
            include_member_count=include_member_count,
            include_role=include_role,
        )
