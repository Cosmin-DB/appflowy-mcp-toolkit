from __future__ import annotations

import builtins
from typing import Any

from appflowy_mcp_toolkit.client import AppFlowyClient


class DatabasesService:
    def __init__(self, client: AppFlowyClient):
        self.client = client

    def list(self, workspace_id: str) -> builtins.list[dict[str, Any]]:
        return self.client.list_databases(workspace_id)

    def fields(self, workspace_id: str, database_id: str) -> builtins.list[dict[str, Any]]:
        return self.client.list_database_fields(workspace_id, database_id)
