from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from appflowy_mcp_toolkit.config import AppFlowyConfig


class ClientCore:
    """Typing surface shared by AppFlowyClient mixins.

    Runtime implementations live on AppFlowyClient or peer mixins. These stubs
    keep mypy honest without importing AppFlowyClient back into its parts.
    """

    config: AppFlowyConfig

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        require_auth: bool = True,
        _retry_refresh: bool = True,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def request_bytes(
        self,
        method: str,
        path: str,
        *,
        content: bytes,
        content_type: str = "application/octet-stream",
        require_auth: bool = True,
        _retry_refresh: bool = True,
    ) -> bytes:
        raise NotImplementedError

    def request_content_json(
        self,
        method: str,
        path: str,
        *,
        content: bytes,
        content_type: str = "application/octet-stream",
        require_auth: bool = True,
        _retry_refresh: bool = True,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def request_bytes_with_headers(
        self,
        method: str,
        path: str,
        *,
        require_auth: bool = True,
        _retry_refresh: bool = True,
    ) -> tuple[str, bytes]:
        raise NotImplementedError

    def _url(self, path: str) -> str:
        raise NotImplementedError

    def _require_writes_enabled(self) -> None:
        raise NotImplementedError

    def _require_publish_writes_enabled(self) -> None:
        raise NotImplementedError

    def _extract_data(self, data: dict[str, Any]) -> Any:
        raise NotImplementedError

    def _extract_list(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        raise NotImplementedError

    def list_database_fields(self, workspace_id: str, database_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    def list_select_options(
        self, workspace_id: str, database_id: str, *, field_name: str = "Status"
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    def get_database_rows(
        self,
        workspace_id: str,
        database_id: str,
        ids: Iterable[str],
        *,
        with_doc: bool = False,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    def list_database_row_ids(self, workspace_id: str, database_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    def get_database_row_orders(self, workspace_id: str, database_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    def get_collab_json(
        self,
        workspace_id: str,
        object_id: str,
        *,
        collab_type: str | int = "Database",
        summary_only: bool = True,
        include_raw: bool = False,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def get_binary_collab(
        self,
        workspace_id: str,
        object_id: str,
        *,
        collab_type: str | int = "Database",
    ) -> dict[str, Any]:
        raise NotImplementedError

    def get_database_blob_diff_summary(
        self,
        workspace_id: str,
        database_id: str,
        *,
        version: int = 1,
        max_known_rid: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def delete_database_row_collab(
        self,
        workspace_id: str,
        database_id: str,
        row_id: str,
        *,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        raise NotImplementedError
