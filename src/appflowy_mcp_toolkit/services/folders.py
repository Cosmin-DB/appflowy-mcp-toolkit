from __future__ import annotations

from typing import Any

from appflowy_mcp_toolkit.client import AppFlowyClient


class FoldersService:
    def __init__(self, client: AppFlowyClient):
        self.client = client

    def get_tree(
        self,
        workspace_id: str,
        *,
        depth: int | None = None,
        root_view_id: str | None = None,
    ) -> dict[str, Any]:
        return self.client.get_folder(workspace_id, depth=depth, root_view_id=root_view_id)
