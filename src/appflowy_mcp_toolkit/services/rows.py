from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from appflowy_mcp_toolkit.client import AppFlowyClient


class RowsService:
    def __init__(self, client: AppFlowyClient):
        self.client = client

    def list_ids(self, workspace_id: str, database_id: str) -> list[dict[str, Any]]:
        return self.client.list_database_row_ids(workspace_id, database_id)

    def details(
        self,
        workspace_id: str,
        database_id: str,
        ids: Iterable[str],
        *,
        with_doc: bool = False,
    ) -> list[dict[str, Any]]:
        return self.client.get_database_rows(workspace_id, database_id, ids, with_doc=with_doc)
