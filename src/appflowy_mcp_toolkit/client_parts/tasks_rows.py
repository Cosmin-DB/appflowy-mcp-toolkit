from __future__ import annotations

from typing import Any

from appflowy_mcp_toolkit.client_parts.base import ClientCore
from appflowy_mcp_toolkit.client_parts.helpers import _collab_type_int, _extract_row_id
from appflowy_mcp_toolkit.errors import AppFlowyError, AppFlowySchemaError
from appflowy_mcp_toolkit.typed_fields import build_cells, build_collab_cell_updates


class TaskRowMixin(ClientCore):
    def create_database_row(
        self,
        workspace_id: str,
        database_id: str,
        *,
        cells: dict[str, Any] | None = None,
        document: str | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if cells is not None:
            payload["cells"] = cells
        if document is not None:
            payload["document"] = document
        path = f"/api/workspace/{workspace_id}/database/{database_id}/row"
        if dry_run:
            return {"dry_run": True, "method": "POST", "path": path, "json": payload}
        self._require_writes_enabled()
        return self.request("POST", path, json=payload)

    def create_database_row_verified(
        self,
        workspace_id: str,
        database_id: str,
        *,
        cells: dict[str, Any] | None = None,
        document: str | None = None,
        dry_run: bool = True,
        include_blob_diff: bool = True,
    ) -> dict[str, Any]:
        """Create one row and verify server-side visibility after the write.

        AppFlowy Web Board can render stale/empty state even when the row is
        already present in REST and collab state. This helper makes that
        distinction explicit: it verifies the data-plane signals we can trust
        programmatically, and leaves UI rendering to live/browser tests.
        """
        create_result = self.create_database_row(
            workspace_id,
            database_id,
            cells=cells,
            document=document,
            dry_run=dry_run,
        )
        if dry_run:
            return {
                **create_result,
                "verification": {
                    "would_check": [
                        "REST row list",
                        "REST row detail",
                        "database row_orders",
                        "DatabaseRow collab JSON",
                        *(["database blob/diff"] if include_blob_diff else []),
                    ],
                },
            }

        row_id = _extract_row_id(create_result)
        if row_id is None:
            raise AppFlowySchemaError(
                "Create row response did not include a row id", payload=create_result
            )

        return {
            "create": create_result,
            "verification": self.verify_database_row(
                workspace_id,
                database_id,
                row_id,
                include_blob_diff=include_blob_diff,
            ),
        }

    def create_typed_database_row(
        self,
        workspace_id: str,
        database_id: str,
        *,
        values: dict[str, Any],
        document: str | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        fields = self.list_database_fields(workspace_id, database_id)
        cells = build_cells(fields, values)
        result = self.create_database_row(
            workspace_id,
            database_id,
            cells=cells,
            document=document,
            dry_run=dry_run,
        )
        return {"typed_cells": cells, "result": result}

    def create_typed_database_row_verified(
        self,
        workspace_id: str,
        database_id: str,
        *,
        values: dict[str, Any],
        document: str | None = None,
        dry_run: bool = True,
        include_blob_diff: bool = True,
    ) -> dict[str, Any]:
        fields = self.list_database_fields(workspace_id, database_id)
        cells = build_cells(fields, values)
        result = self.create_database_row_verified(
            workspace_id,
            database_id,
            cells=cells,
            document=document,
            dry_run=dry_run,
            include_blob_diff=include_blob_diff,
        )
        return {"typed_cells": cells, "result": result}

    def upsert_database_row(
        self,
        workspace_id: str,
        database_id: str,
        *,
        pre_hash: str | None = None,
        cells: dict[str, Any] | None = None,
        document: str | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if pre_hash is not None:
            payload["pre_hash"] = pre_hash
        if cells is not None:
            payload["cells"] = cells
        if document is not None:
            payload["document"] = document
        path = f"/api/workspace/{workspace_id}/database/{database_id}/row"
        if dry_run:
            return {"dry_run": True, "method": "PUT", "path": path, "json": payload}
        self._require_writes_enabled()
        return self.request("PUT", path, json=payload)

    def upsert_typed_database_row(
        self,
        workspace_id: str,
        database_id: str,
        *,
        values: dict[str, Any],
        pre_hash: str | None = None,
        document: str | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        fields = self.list_database_fields(workspace_id, database_id)
        cells = build_cells(fields, values)
        result = self.upsert_database_row(
            workspace_id,
            database_id,
            pre_hash=pre_hash,
            cells=cells,
            document=document,
            dry_run=dry_run,
        )
        return {"typed_cells": cells, "result": result}

    def upsert_managed_task(
        self,
        workspace_id: str,
        database_id: str,
        *,
        task_key: str,
        description: str | None = None,
        status: str | None = None,
        document: str | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        cells: dict[str, Any] = {}
        if description is not None:
            cells["Description"] = description
        if status is not None:
            cells["Status"] = status
        return self.upsert_database_row(
            workspace_id,
            database_id,
            pre_hash=task_key,
            cells=cells or None,
            document=document,
            dry_run=dry_run,
        )

    def upsert_managed_task_verified(
        self,
        workspace_id: str,
        database_id: str,
        *,
        task_key: str,
        description: str | None = None,
        status: str | None = None,
        document: str | None = None,
        dry_run: bool = True,
        include_blob_diff: bool = True,
    ) -> dict[str, Any]:
        """Create/update an MCP-managed task and verify its data-plane state."""
        result = self.upsert_managed_task(
            workspace_id,
            database_id,
            task_key=task_key,
            description=description,
            status=status,
            document=document,
            dry_run=dry_run,
        )
        if dry_run:
            return {
                **result,
                "verification": {
                    "would_check": [
                        "REST row list",
                        "REST row detail",
                        "database row_orders",
                        "DatabaseRow collab JSON",
                        *(["database blob/diff"] if include_blob_diff else []),
                    ],
                },
            }
        row_id = _extract_row_id(result)
        if row_id is None:
            raise AppFlowySchemaError(
                "Managed task upsert response did not include a row id", payload=result
            )
        return {
            "upsert": result,
            "verification": self.verify_database_row(
                workspace_id,
                database_id,
                row_id,
                include_blob_diff=include_blob_diff,
            ),
        }

    def move_managed_task_status(
        self,
        workspace_id: str,
        database_id: str,
        *,
        task_key: str,
        status: str,
        dry_run: bool = True,
        validate_status: bool = True,
    ) -> dict[str, Any]:
        if validate_status:
            valid = [
                item.get("name") for item in self.list_select_options(workspace_id, database_id)
            ]
            if status not in valid:
                raise AppFlowyError(f"Invalid Status option: {status}. Valid options: {valid}")
        result = self.upsert_managed_task(
            workspace_id,
            database_id,
            task_key=task_key,
            status=status,
            dry_run=dry_run,
        )
        row_id = result.get("data")
        if not dry_run and isinstance(row_id, str):
            result = {
                **result,
                "verified_row": self.get_database_rows(workspace_id, database_id, [row_id]),
                "verification": self.verify_database_row(
                    workspace_id,
                    database_id,
                    row_id,
                    include_blob_diff=False,
                ),
            }
        return result

    def list_tasks(
        self,
        workspace_id: str,
        database_id: str,
        *,
        with_doc: bool = False,
    ) -> dict[str, Any]:
        """List task rows from one AppFlowy database with current row details."""
        row_ids: list[str] = []
        for item in self.list_database_row_ids(workspace_id, database_id):
            row_id = item.get("id")
            if isinstance(row_id, str):
                row_ids.append(row_id)
        rows = self.get_database_rows(workspace_id, database_id, row_ids, with_doc=with_doc)
        return {"row_ids": row_ids, "rows": rows}

    def search_tasks_by_description(
        self,
        workspace_id: str,
        database_id: str,
        description: str,
        *,
        mode: str = "contains",
        case_sensitive: bool = False,
        with_doc: bool = False,
    ) -> dict[str, Any]:
        """Find task rows by human-visible Description text."""
        if mode not in {"exact", "contains"}:
            raise AppFlowyError("mode must be 'exact' or 'contains'")
        tasks = self.list_tasks(workspace_id, database_id, with_doc=with_doc)
        matches = []
        needle = description if case_sensitive else description.casefold()
        for row in tasks["rows"]:
            text = self._task_description_text(row)
            haystack = text if case_sensitive else text.casefold()
            matched = haystack == needle if mode == "exact" else needle in haystack
            if matched:
                matches.append(self._task_candidate(row, description_text=text))
        return {
            "description": description,
            "mode": mode,
            "case_sensitive": case_sensitive,
            "match_count": len(matches),
            "matches": matches,
        }

    def resolve_task_by_description(
        self,
        workspace_id: str,
        database_id: str,
        description: str,
        *,
        mode: str = "exact",
        case_sensitive: bool = False,
    ) -> dict[str, Any]:
        """Resolve a human task name only when it maps to exactly one row."""
        search = self.search_tasks_by_description(
            workspace_id,
            database_id,
            description,
            mode=mode,
            case_sensitive=case_sensitive,
        )
        matches = search["matches"]
        if len(matches) == 1:
            return {"status": "resolved", "match": matches[0], "search": search}
        status = "not_found" if not matches else "ambiguous"
        return {
            "status": status,
            "message": (
                "No task matched the Description text."
                if status == "not_found"
                else "Multiple tasks matched the Description text; no action was taken."
            ),
            "candidates": matches,
            "search": search,
        }

    def create_task(
        self,
        workspace_id: str,
        database_id: str,
        *,
        task_key: str,
        description: str,
        status: str = "To Do",
        document: str | None = None,
        dry_run: bool = True,
        include_blob_diff: bool = True,
    ) -> dict[str, Any]:
        """Create a user-visible task row using AppFlowy's normal row-create route.

        The deterministic ``pre_hash`` upsert route is still available through
        ``upsert_managed_task_verified`` for idempotent agent-owned tasks, but
        browser testing showed that freshly upserted rows can verify through the
        data plane while AppFlowy Web Grid does not render them. The public
        create helper therefore favors the browser-visible POST row path.
        """
        created = self.create_database_row_verified(
            workspace_id,
            database_id,
            cells={"Description": description, "Status": status},
            document=document,
            dry_run=dry_run,
            include_blob_diff=include_blob_diff,
        )
        return {"task_key": task_key, **created}

    def update_task(
        self,
        workspace_id: str,
        database_id: str,
        *,
        task_key: str,
        description: str | None = None,
        status: str | None = None,
        document: str | None = None,
        dry_run: bool = True,
        include_blob_diff: bool = True,
    ) -> dict[str, Any]:
        """Update an MCP-managed task by its stable task key."""
        return self.upsert_managed_task_verified(
            workspace_id,
            database_id,
            task_key=task_key,
            description=description,
            status=status,
            document=document,
            dry_run=dry_run,
            include_blob_diff=include_blob_diff,
        )

    def move_task(
        self,
        workspace_id: str,
        database_id: str,
        *,
        task_key: str,
        status: str,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Move an MCP-managed task to a status group."""
        return self.move_managed_task_status(
            workspace_id,
            database_id,
            task_key=task_key,
            status=status,
            dry_run=dry_run,
        )

    def update_task_by_description(
        self,
        workspace_id: str,
        database_id: str,
        description: str,
        *,
        new_description: str | None = None,
        status: str | None = None,
        match_mode: str = "exact",
        case_sensitive: bool = False,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Update a task resolved by Description text, refusing duplicates."""
        values: dict[str, Any] = {}
        if new_description is not None:
            values["Description"] = new_description
        if status is not None:
            values["Status"] = status
        if not values:
            raise AppFlowyError("At least one update value is required")
        resolution = self.resolve_task_by_description(
            workspace_id,
            database_id,
            description,
            mode=match_mode,
            case_sensitive=case_sensitive,
        )
        if resolution["status"] != "resolved":
            return {**resolution, "dry_run": dry_run, "operation": "update_task_by_description"}
        row_id = resolution["match"].get("row_id")
        if not isinstance(row_id, str):
            raise AppFlowySchemaError("Resolved task did not include a row id", payload=resolution)
        return {
            "status": "updated" if not dry_run else "resolved_dry_run",
            "resolution": resolution,
            "result": self.update_database_row_by_id_collab(
                workspace_id,
                database_id,
                row_id,
                values=values,
                dry_run=dry_run,
            ),
        }

    def move_task_by_description(
        self,
        workspace_id: str,
        database_id: str,
        description: str,
        *,
        status: str,
        match_mode: str = "exact",
        case_sensitive: bool = False,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Move a task resolved by Description text, refusing duplicates."""
        resolution = self.resolve_task_by_description(
            workspace_id,
            database_id,
            description,
            mode=match_mode,
            case_sensitive=case_sensitive,
        )
        if resolution["status"] != "resolved":
            return {**resolution, "dry_run": dry_run, "operation": "move_task_by_description"}
        row_id = resolution["match"].get("row_id")
        if not isinstance(row_id, str):
            raise AppFlowySchemaError("Resolved task did not include a row id", payload=resolution)
        return {
            "status": "moved" if not dry_run else "resolved_dry_run",
            "resolution": resolution,
            "result": self.move_task_by_row_id(
                workspace_id,
                database_id,
                row_id,
                status=status,
                dry_run=dry_run,
            ),
        }

    def update_database_row_by_id_collab(
        self,
        workspace_id: str,
        database_id: str,
        row_id: str,
        *,
        values: dict[str, Any],
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Update an existing row by row id through its DatabaseRow collab document.

        Use this for rows created manually in AppFlowy Web or rows where only the
        row_id is known. REST upsert is still preferred for MCP-managed rows that
        have a stable pre_hash/task_key.
        """
        from appflowy_mcp_toolkit.collab.collab_delete import (
            CollabHelperError,
            allow_collab_writes,
            invoke_yjs_update_row_cells,
        )

        fields = self.list_database_fields(workspace_id, database_id)
        typed_cells = build_cells(fields, values)
        cell_updates = build_collab_cell_updates(fields, values)

        if not dry_run:
            self._require_writes_enabled()
            if not allow_collab_writes():
                raise AppFlowyError(
                    "Collab writes are disabled. "
                    "Set APPFLOWY_ALLOW_COLLAB_WRITES=true to enable Yjs-based row updates."
                )

        binary = self.get_binary_collab(workspace_id, row_id, collab_type="DatabaseRow")
        doc_state: list[int] = binary.get("doc_state", [])
        if not doc_state:
            raise AppFlowyError(
                "Binary DatabaseRow collab returned empty doc_state; cannot compute update delta."
            )

        try:
            helper_result = invoke_yjs_update_row_cells(doc_state, cell_updates)
        except CollabHelperError as exc:
            raise AppFlowyError(str(exc)) from exc

        summary: dict[str, Any] = {
            "dry_run": dry_run,
            "row_id": row_id,
            "typed_cells": typed_cells,
            "collab_cell_updates": cell_updates,
            "updated_fields": helper_result["updated_fields"],
            "delta_update_bytes": len(helper_result["delta_update"]),
            "path": f"/api/workspace/v1/{workspace_id}/collab/{row_id}/web-update",
            "collab_type": _collab_type_int("DatabaseRow"),
        }
        if dry_run:
            return summary

        post_data = self.request(
            "POST",
            f"/api/workspace/v1/{workspace_id}/collab/{row_id}/web-update",
            json={
                "doc_state": helper_result["delta_update"],
                "collab_type": _collab_type_int("DatabaseRow"),
            },
        )
        summary["server_status"] = post_data.get("code")
        summary["verified_row"] = self.get_database_rows(workspace_id, database_id, [row_id])
        summary["verification"] = self.verify_database_row(
            workspace_id,
            database_id,
            row_id,
            include_blob_diff=False,
        )
        return summary

    def move_task_by_row_id(
        self,
        workspace_id: str,
        database_id: str,
        row_id: str,
        *,
        status: str,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Move an existing/manual task row to another Status option by row id."""
        return self.update_database_row_by_id_collab(
            workspace_id,
            database_id,
            row_id,
            values={"Status": status},
            dry_run=dry_run,
        )

    def delete_task(
        self,
        workspace_id: str,
        database_id: str,
        row_id: str,
        *,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Delete a task row from all database views.

        Deletion currently requires the AppFlowy row id. The stable task_key
        is used for create/update/move, but AppFlowy does not expose a safe
        lookup-by-pre_hash endpoint, and delete must not create a missing task
        just to discover its row id.
        """
        return self.delete_database_row_collab(
            workspace_id,
            database_id,
            row_id,
            dry_run=dry_run,
        )

    def delete_task_by_description(
        self,
        workspace_id: str,
        database_id: str,
        description: str,
        *,
        match_mode: str = "exact",
        case_sensitive: bool = False,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Delete a task resolved by Description text, refusing duplicates."""
        resolution = self.resolve_task_by_description(
            workspace_id,
            database_id,
            description,
            mode=match_mode,
            case_sensitive=case_sensitive,
        )
        if resolution["status"] != "resolved":
            return {**resolution, "dry_run": dry_run, "operation": "delete_task_by_description"}
        row_id = resolution["match"].get("row_id")
        if not isinstance(row_id, str):
            raise AppFlowySchemaError("Resolved task did not include a row id", payload=resolution)
        return {
            "status": "deleted" if not dry_run else "resolved_dry_run",
            "resolution": resolution,
            "result": self.delete_task(
                workspace_id,
                database_id,
                row_id,
                dry_run=dry_run,
            ),
        }

    def _task_candidate(cls, row: dict[str, Any], *, description_text: str) -> dict[str, Any]:
        cells = row.get("cells") if isinstance(row.get("cells"), dict) else {}
        return {
            "row_id": row.get("id") or row.get("row_id"),
            "description": description_text,
            "status": cells.get("Status") if isinstance(cells, dict) else None,
        }

    def _task_description_text(cls, row: dict[str, Any]) -> str:
        cells = row.get("cells")
        if not isinstance(cells, dict):
            return ""
        return " ".join(cls._flatten_cell_text(cells.get("Description"))).strip()

    def _flatten_cell_text(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, (bool, int, float)):
            return [str(value)]
        if isinstance(value, list):
            parts: list[str] = []
            for item in value:
                parts.extend(cls._flatten_cell_text(item))
            return parts
        if isinstance(value, dict):
            preferred: list[str] = []
            for key in ("text", "content", "insert", "value", "data"):
                if key in value:
                    preferred.extend(cls._flatten_cell_text(value[key]))
            if preferred:
                return preferred
            parts = []
            for item in value.values():
                parts.extend(cls._flatten_cell_text(item))
            return parts
        return [str(value)]

    def verify_database_row(
        self,
        workspace_id: str,
        database_id: str,
        row_id: str,
        *,
        include_blob_diff: bool = True,
    ) -> dict[str, Any]:
        """Verify one row through AppFlowy's API/collab data-plane signals."""
        row_list = self.list_database_row_ids(workspace_id, database_id)
        row_detail = self.get_database_rows(workspace_id, database_id, [row_id], with_doc=True)
        row_orders = self.get_database_row_orders(workspace_id, database_id)

        views_containing_row = [
            entry["view_id"] for entry in row_orders if row_id in entry.get("row_orders", [])
        ]
        verification: dict[str, Any] = {
            "row_id": row_id,
            "rest_row_list_present": any(item.get("id") == row_id for item in row_list),
            "rest_row_detail_present": bool(row_detail),
            "row_orders_present": bool(views_containing_row),
            "views_containing_row": views_containing_row,
            "ui_note": (
                "This verifies AppFlowy's data plane. AppFlowy Web Board may still "
                "require Grid/refresh warm-up before rendering the card."
            ),
        }

        try:
            row_collab = self.get_collab_json(workspace_id, row_id, collab_type="DatabaseRow")
            verification["database_row_collab_present"] = bool(row_collab)
        except AppFlowyError as exc:
            verification["database_row_collab_present"] = None
            verification["database_row_collab_error"] = str(exc)

        if include_blob_diff:
            try:
                blob_diff = self.get_database_blob_diff_summary(workspace_id, database_id)
                blob_rows = [
                    item
                    for item in blob_diff.get("rows", [])
                    if isinstance(item, dict) and item.get("row_id") == row_id
                ]
                verification["blob_diff_status_name"] = blob_diff.get("status_name")
                verification["blob_diff_row_operations"] = [
                    item.get("operation") for item in blob_rows
                ]
                verification["blob_diff_row_present"] = bool(blob_rows)
            except AppFlowyError as exc:
                verification["blob_diff_status_name"] = None
                verification["blob_diff_row_present"] = None
                verification["blob_diff_error"] = str(exc)

        verification["verified"] = all(
            [
                verification["rest_row_list_present"],
                verification["rest_row_detail_present"],
                verification["row_orders_present"],
                verification["database_row_collab_present"] is True,
            ]
        )
        return verification
