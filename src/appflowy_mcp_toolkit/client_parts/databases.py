from __future__ import annotations

import secrets
from collections.abc import Iterable
from typing import Any

from appflowy_mcp_toolkit.client_parts.base import ClientCore
from appflowy_mcp_toolkit.client_parts.helpers import _collab_type_int
from appflowy_mcp_toolkit.errors import AppFlowyError, AppFlowySchemaError


class DatabaseMixin(ClientCore):
    def list_databases(self, workspace_id: str) -> list[dict[str, Any]]:
        data = self.request("GET", f"/api/workspace/{workspace_id}/database")
        return self._extract_list(data)

    def list_database_fields(self, workspace_id: str, database_id: str) -> list[dict[str, Any]]:
        data = self.request("GET", f"/api/workspace/{workspace_id}/database/{database_id}/fields")
        return self._extract_list(data)

    def create_database_field(
        self,
        workspace_id: str,
        database_id: str,
        *,
        name: str,
        field_type: int,
        type_option_data: dict[str, Any] | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": name, "field_type": field_type}
        if type_option_data is not None:
            payload["type_option_data"] = type_option_data
        path = f"/api/workspace/{workspace_id}/database/{database_id}/fields"
        if dry_run:
            return {"dry_run": True, "method": "POST", "path": path, "json": payload}
        self._require_writes_enabled()
        return self.request("POST", path, json=payload)

    def list_select_options(
        self, workspace_id: str, database_id: str, *, field_name: str = "Status"
    ) -> list[dict[str, Any]]:
        fields = self.list_database_fields(workspace_id, database_id)
        field = next((item for item in fields if item.get("name") == field_name), None)
        if field is None:
            raise AppFlowyError(f"Field not found: {field_name}")
        options = field.get("type_option", {}).get("content", {}).get("options", [])
        if not isinstance(options, list):
            return []
        return [item for item in options if isinstance(item, dict)]

    def add_select_option_collab(
        self,
        workspace_id: str,
        database_id: str,
        *,
        field_name: str = "Status",
        name: str,
        color: str = "Purple",
        option_id: str | None = None,
        view_id: str | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Add an option to a select field through Database collab.

        In board views, columns are not standalone objects. They are select
        options from the grouped field, usually ``Status``. AppFlowy Web also
        keeps a board group list in the Database collab, so this updates both
        the field option list and matching board groups.
        """
        from appflowy_mcp_toolkit.collab.collab_delete import (
            CollabHelperError,
            allow_collab_writes,
            invoke_yjs_add_select_option,
        )

        fields = self.list_database_fields(workspace_id, database_id)
        field = next((item for item in fields if item.get("name") == field_name), None)
        if field is None:
            raise AppFlowyError(f"Field not found: {field_name}")
        field_id = str(field.get("id") or "")
        field_type_id = field.get("field_type_id")
        if not field_id or not isinstance(field_type_id, int):
            raise AppFlowySchemaError("Select field metadata is incomplete", payload=field)
        if field_type_id not in {3, 4}:
            raise AppFlowyError(
                f"Field {field_name!r} is not a select field; field_type_id={field_type_id}"
            )

        existing_options = self.list_select_options(
            workspace_id,
            database_id,
            field_name=field_name,
        )
        existing = next((item for item in existing_options if item.get("name") == name), None)
        resolved_option_id = (option_id or str(existing.get("id"))) if existing else option_id
        if resolved_option_id is None:
            resolved_option_id = "mcp_" + secrets.token_urlsafe(4).replace("-", "_")

        if not dry_run:
            self._require_writes_enabled()
            if not allow_collab_writes():
                raise AppFlowyError(
                    "Collab writes are disabled. "
                    "Set APPFLOWY_ALLOW_COLLAB_WRITES=true to enable Yjs-based schema updates."
                )

        binary = self.get_binary_collab(workspace_id, database_id, collab_type="Database")
        doc_state: list[int] = binary.get("doc_state", [])
        if not doc_state:
            raise AppFlowyError(
                "Binary Database collab returned empty doc_state; cannot compute option delta."
            )

        try:
            helper_result = invoke_yjs_add_select_option(
                doc_state,
                field_id=field_id,
                field_type=field_type_id,
                option_id=resolved_option_id,
                name=name,
                color=color,
                view_id=view_id,
            )
        except CollabHelperError as exc:
            raise AppFlowyError(str(exc)) from exc

        summary: dict[str, Any] = {
            "dry_run": dry_run,
            "database_id": database_id,
            "field_id": field_id,
            "field_name": field_name,
            "option": helper_result["option"],
            "option_added": helper_result["option_added"],
            "affected_views": helper_result["affected_views"],
            "delta_update_bytes": len(helper_result["delta_update"]),
            "path": f"/api/workspace/v1/{workspace_id}/collab/{database_id}/web-update",
            "collab_type": _collab_type_int("Database"),
        }
        if dry_run:
            return summary

        post_data = self.request(
            "POST",
            f"/api/workspace/v1/{workspace_id}/collab/{database_id}/web-update",
            json={
                "doc_state": helper_result["delta_update"],
                "collab_type": _collab_type_int("Database"),
            },
        )
        summary["server_status"] = post_data.get("code")
        summary["verified_options"] = self.list_select_options(
            workspace_id,
            database_id,
            field_name=field_name,
        )
        return summary

    def _select_field_metadata(
        self, workspace_id: str, database_id: str, *, field_name: str
    ) -> tuple[str, int]:
        fields = self.list_database_fields(workspace_id, database_id)
        field = next((item for item in fields if item.get("name") == field_name), None)
        if field is None:
            raise AppFlowyError(f"Field not found: {field_name}")
        field_id = str(field.get("id") or "")
        field_type_id = field.get("field_type_id")
        if not field_id or not isinstance(field_type_id, int):
            raise AppFlowySchemaError("Select field metadata is incomplete", payload=field)
        if field_type_id not in {3, 4}:
            raise AppFlowyError(
                f"Field {field_name!r} is not a select field; field_type_id={field_type_id}"
            )
        return field_id, field_type_id

    def _resolve_select_option_ref(
        self,
        workspace_id: str,
        database_id: str,
        *,
        field_name: str,
        option_id: str | None = None,
        option_name: str | None = None,
    ) -> tuple[str | None, str | None, dict[str, Any]]:
        if not option_id and not option_name:
            raise AppFlowyError("Provide option_id or option_name")
        options = self.list_select_options(workspace_id, database_id, field_name=field_name)
        existing = next(
            (
                item
                for item in options
                if (option_id and item.get("id") == option_id)
                or (option_name and item.get("name") == option_name)
            ),
            None,
        )
        if existing is None:
            label = option_id if option_id else option_name
            raise AppFlowyError(f"Select option not found: {label}")
        return str(existing.get("id")), str(existing.get("name")), existing

    def rename_select_option_collab(
        self,
        workspace_id: str,
        database_id: str,
        *,
        field_name: str = "Status",
        new_name: str,
        option_id: str | None = None,
        option_name: str | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Rename a select option through Database collab. Dry-run by default."""
        from appflowy_mcp_toolkit.collab.collab_delete import (
            CollabHelperError,
            allow_collab_writes,
            invoke_yjs_rename_select_option,
        )

        field_id, field_type_id = self._select_field_metadata(
            workspace_id, database_id, field_name=field_name
        )
        resolved_option_id, resolved_option_name, _option = self._resolve_select_option_ref(
            workspace_id,
            database_id,
            field_name=field_name,
            option_id=option_id,
            option_name=option_name,
        )
        if not dry_run:
            self._require_writes_enabled()
            if not allow_collab_writes():
                raise AppFlowyError(
                    "Collab writes are disabled. "
                    "Set APPFLOWY_ALLOW_COLLAB_WRITES=true to enable Yjs-based schema updates."
                )

        binary = self.get_binary_collab(workspace_id, database_id, collab_type="Database")
        doc_state: list[int] = binary.get("doc_state", [])
        if not doc_state:
            raise AppFlowyError(
                "Binary Database collab returned empty doc_state; cannot compute option delta."
            )

        try:
            helper_result = invoke_yjs_rename_select_option(
                doc_state,
                field_id=field_id,
                field_type=field_type_id,
                option_id=resolved_option_id,
                option_name=resolved_option_name,
                new_name=new_name,
            )
        except CollabHelperError as exc:
            raise AppFlowyError(str(exc)) from exc

        summary: dict[str, Any] = {
            "dry_run": dry_run,
            "database_id": database_id,
            "field_id": field_id,
            "field_name": field_name,
            "option_id": helper_result["option_id"],
            "previous_name": helper_result["previous_name"],
            "option": helper_result["option"],
            "renamed": helper_result["renamed"],
            "delta_update_bytes": len(helper_result["delta_update"]),
            "path": f"/api/workspace/v1/{workspace_id}/collab/{database_id}/web-update",
            "collab_type": _collab_type_int("Database"),
        }
        if dry_run:
            return summary

        post_data = self.request(
            "POST",
            f"/api/workspace/v1/{workspace_id}/collab/{database_id}/web-update",
            json={
                "doc_state": helper_result["delta_update"],
                "collab_type": _collab_type_int("Database"),
            },
        )
        summary["server_status"] = post_data.get("code")
        summary["verified_options"] = self.list_select_options(
            workspace_id, database_id, field_name=field_name
        )
        return summary

    def set_select_option_visibility_collab(
        self,
        workspace_id: str,
        database_id: str,
        *,
        field_name: str = "Status",
        visible: bool,
        option_id: str | None = None,
        option_name: str | None = None,
        view_id: str | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Show or hide a select option in board view groups. Dry-run by default."""
        from appflowy_mcp_toolkit.collab.collab_delete import (
            CollabHelperError,
            allow_collab_writes,
            invoke_yjs_set_select_option_visibility,
        )

        field_id, field_type_id = self._select_field_metadata(
            workspace_id, database_id, field_name=field_name
        )
        resolved_option_id, resolved_option_name, _option = self._resolve_select_option_ref(
            workspace_id,
            database_id,
            field_name=field_name,
            option_id=option_id,
            option_name=option_name,
        )
        if not dry_run:
            self._require_writes_enabled()
            if not allow_collab_writes():
                raise AppFlowyError(
                    "Collab writes are disabled. "
                    "Set APPFLOWY_ALLOW_COLLAB_WRITES=true to enable Yjs-based schema updates."
                )

        binary = self.get_binary_collab(workspace_id, database_id, collab_type="Database")
        doc_state: list[int] = binary.get("doc_state", [])
        if not doc_state:
            raise AppFlowyError(
                "Binary Database collab returned empty doc_state; cannot compute option delta."
            )

        try:
            helper_result = invoke_yjs_set_select_option_visibility(
                doc_state,
                field_id=field_id,
                field_type=field_type_id,
                option_id=resolved_option_id,
                option_name=resolved_option_name,
                visible=visible,
                view_id=view_id,
            )
        except CollabHelperError as exc:
            raise AppFlowyError(str(exc)) from exc

        summary: dict[str, Any] = {
            "dry_run": dry_run,
            "database_id": database_id,
            "field_id": field_id,
            "field_name": field_name,
            "option": helper_result["option"],
            "visible": helper_result["visible"],
            "affected_views": helper_result["affected_views"],
            "visibility_by_view": helper_result["visibility_by_view"],
            "delta_update_bytes": len(helper_result["delta_update"]),
            "path": f"/api/workspace/v1/{workspace_id}/collab/{database_id}/web-update",
            "collab_type": _collab_type_int("Database"),
        }
        if dry_run:
            return summary

        post_data = self.request(
            "POST",
            f"/api/workspace/v1/{workspace_id}/collab/{database_id}/web-update",
            json={
                "doc_state": helper_result["delta_update"],
                "collab_type": _collab_type_int("Database"),
            },
        )
        summary["server_status"] = post_data.get("code")
        return summary

    def list_database_row_ids(self, workspace_id: str, database_id: str) -> list[dict[str, Any]]:
        data = self.request("GET", f"/api/workspace/{workspace_id}/database/{database_id}/row")
        return self._extract_list(data)

    def list_updated_database_rows(
        self,
        workspace_id: str,
        database_id: str,
        *,
        after: str | None = None,
    ) -> list[dict[str, Any]]:
        params = {"after": after} if after else None
        data = self.request(
            "GET",
            f"/api/workspace/{workspace_id}/database/{database_id}/row/updated",
            params=params,
        )
        return self._extract_list(data)

    def list_quick_notes(
        self,
        workspace_id: str,
        *,
        search_term: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if search_term is not None:
            params["search_term"] = search_term
        if offset is not None:
            params["offset"] = offset
        if limit is not None:
            params["limit"] = limit
        data = self.request(
            "GET",
            f"/api/workspace/{workspace_id}/quick-note",
            params=params or None,
        )
        quick_notes = self._extract_data(data)
        if not isinstance(quick_notes, dict):
            raise AppFlowySchemaError("Expected AppFlowy quick notes response", payload=data)
        return quick_notes

    def create_quick_note(
        self,
        workspace_id: str,
        *,
        data: Any | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        payload = {"data": data}
        path = f"/api/workspace/{workspace_id}/quick-note"
        if dry_run:
            return {"dry_run": True, "method": "POST", "path": path, "json": payload}
        self._require_writes_enabled()
        response = self.request("POST", path, json=payload)
        quick_note = self._extract_data(response)
        if not isinstance(quick_note, dict):
            raise AppFlowySchemaError("Expected AppFlowy quick note response", payload=response)
        return quick_note

    def update_quick_note(
        self,
        workspace_id: str,
        quick_note_id: str,
        *,
        data: Any,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        payload = {"data": data}
        path = f"/api/workspace/{workspace_id}/quick-note/{quick_note_id}"
        if dry_run:
            return {"dry_run": True, "method": "PUT", "path": path, "json": payload}
        self._require_writes_enabled()
        return self.request("PUT", path, json=payload)

    def delete_quick_note(
        self,
        workspace_id: str,
        quick_note_id: str,
        *,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        path = f"/api/workspace/{workspace_id}/quick-note/{quick_note_id}"
        if dry_run:
            return {"dry_run": True, "method": "DELETE", "path": path}
        self._require_writes_enabled()
        return self.request("DELETE", path)

    def search_documents(
        self,
        workspace_id: str,
        query: str,
        *,
        limit: int | None = None,
        preview_size: int | None = None,
        score: float | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"query": query}
        if limit is not None:
            params["limit"] = limit
        if preview_size is not None:
            params["preview_size"] = preview_size
        if score is not None:
            params["score"] = score
        data = self.request("GET", f"/api/search/{workspace_id}", params=params)
        return self._extract_list(data)

    def get_database_rows(
        self,
        workspace_id: str,
        database_id: str,
        ids: Iterable[str],
        *,
        with_doc: bool = False,
    ) -> list[dict[str, Any]]:
        row_ids = [str(row_id) for row_id in ids if str(row_id)]
        if not row_ids:
            return []
        data = self.request(
            "GET",
            f"/api/workspace/{workspace_id}/database/{database_id}/row/detail",
            params={"ids": ",".join(row_ids), "with_doc": str(with_doc).lower()},
        )
        return self._extract_list(data)
