from __future__ import annotations

from typing import Any

from appflowy_mcp_toolkit.blob_diff import (
    decode_database_blob_diff_response,
    encode_database_blob_diff_request,
)
from appflowy_mcp_toolkit.client_parts.base import ClientCore
from appflowy_mcp_toolkit.client_parts.helpers import (
    _collab_type_int,
    _extract_row_orders,
    _extract_view_configs,
    _summarize_collab,
)
from appflowy_mcp_toolkit.errors import AppFlowyError


class DiagnosticMixin(ClientCore):
    def get_collab_json(
        self,
        workspace_id: str,
        object_id: str,
        *,
        collab_type: str | int = "Database",
        summary_only: bool = True,
        include_raw: bool = False,
    ) -> dict[str, Any]:
        """Fetch a collab document as JSON.

        Uses ``GET /api/workspace/v1/{workspace_id}/collab/{object_id}/json``.

        ``collab_type`` can be a well-known string name or an explicit integer::

            "Document" = 0, "Database" = 1, "WorkspaceDatabase" = 2,
            "Folder" = 3, "DatabaseRow" = 4, "UserAwareness" = 5

        The server requires the integer form; string names are resolved
        automatically.

        Safety parameters
        -----------------
        summary_only : bool
            When ``True``, return only a high-level summary of the collab
            document (top-level keys, type, counts) without the raw body.
            Defaults to ``True`` so public callers do not receive the full raw
            collab body unless explicitly requested.
        include_raw : bool
            When ``False`` and ``summary_only=True``, the raw collab body is
            omitted.  Ignored when ``summary_only=False``.
            Defaults to ``False`` so public callers do not receive the full raw
            collab body unless explicitly requested.

        Internal helpers that need the complete document pass
        ``summary_only=False, include_raw=True`` explicitly.
        """
        data = self.request(
            "GET",
            f"/api/workspace/v1/{workspace_id}/collab/{object_id}/json",
            params={"collab_type": _collab_type_int(collab_type)},
        )
        raw = self._extract_data(data)
        if not summary_only:
            return raw
        return _summarize_collab(
            raw,
            workspace_id=workspace_id,
            object_id=object_id,
            collab_type=str(collab_type),
            include_raw=include_raw,
        )

    def get_database_row_orders(
        self,
        workspace_id: str,
        database_id: str,
    ) -> list[dict[str, Any]]:
        """Return per-view row orders extracted from the database collab document.

        Each entry has ``view_id`` and ``row_orders`` (list of row-id strings).
        Returns an empty list if the collab document has no recognisable views.
        """
        collab = self.get_collab_json(
            workspace_id,
            database_id,
            collab_type="Database",
            summary_only=False,
            include_raw=True,
        )
        return _extract_row_orders(collab)

    def get_database_view_configs(
        self,
        workspace_id: str,
        database_id: str,
    ) -> list[dict[str, Any]]:
        """Return normalized per-view database configuration from collab JSON.

        AppFlowy stores database view configuration in the Database collab
        document, not in the public row REST payload. This read-only helper
        exposes the parts that are useful when assisting a human with a view:
        layout, layout settings, filters, sorts, board/group settings and
        field visibility/width settings.
        """
        collab = self.get_collab_json(
            workspace_id,
            database_id,
            collab_type="Database",
            summary_only=False,
            include_raw=True,
        )
        return _extract_view_configs(collab)

    def get_database_blob_diff_summary(
        self,
        workspace_id: str,
        database_id: str,
        *,
        version: int = 1,
        max_known_rid: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """Fetch and summarise AppFlowy Web's database blob/diff response.

        This is a read-only diagnostic path used by AppFlowy Web to seed row
        documents before rendering database views. The summary omits raw binary
        doc-state bytes but reports row ids, operation type, RID values and
        doc-state sizes so callers can compare REST/collab visibility with the
        browser's blob/diff visibility.
        """
        payload = encode_database_blob_diff_request(
            version=version,
            max_known_rid=max_known_rid,
        )
        response = self.request_bytes(
            "POST",
            f"/api/workspace/{workspace_id}/database/{database_id}/blob/diff",
            content=payload,
        )
        return decode_database_blob_diff_response(response)

    def get_binary_collab(
        self,
        workspace_id: str,
        object_id: str,
        *,
        collab_type: str | int = "Database",
    ) -> dict[str, Any]:
        """Fetch the binary collab state from AppFlowy Cloud.

        Uses ``GET /api/workspace/v1/{workspace_id}/collab/{object_id}``.
        Returns the raw API response dict with ``doc_state`` (list[int]),
        ``state_vector`` (list[int]) and ``version`` (int) fields.
        """
        data = self.request(
            "GET",
            f"/api/workspace/v1/{workspace_id}/collab/{object_id}",
            params={"collab_type": _collab_type_int(collab_type)},
        )
        return self._extract_data(data)

    def delete_database_row_collab(
        self,
        workspace_id: str,
        database_id: str,
        row_id: str,
        *,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Delete a database row via Yjs collab mutation (experimental, M6.3).

        This is the only confirmed-correct delete path: AppFlowy Web does not
        expose a REST row-delete endpoint.  Deletion works by removing the
        ``row_id`` from every view's ``row_orders`` in the database collab
        document and posting the incremental lib0-v1 update to
        ``/api/workspace/v1/{workspace_id}/collab/{database_id}/web-update``.

        **Experimental safety gates (live mode requires all of these):**

        - ``dry_run=False`` must be passed explicitly.
        - ``APPFLOWY_ALLOW_WRITES=true`` must be set in the environment.
        - ``APPFLOWY_ALLOW_COLLAB_WRITES=true`` must be set in the environment.
        - The row must be present in the binary collab (not just the REST row
          list); rows freshly created via REST may not yet be visible in the
          binary collab state due to sync lag.

        **Node.js 18+ and the ``yjs`` npm package are required.**
        Run ``cd src/appflowy_mcp_toolkit/collab && npm install`` once before
        using this method.

        Parameters
        ----------
        workspace_id:
            AppFlowy workspace UUID string.
        database_id:
            AppFlowy database UUID string.
        row_id:
            Row UUID string to delete.
        dry_run:
            If ``True`` (default), compute and return the mutation summary
            without posting to the server.

        Returns
        -------
        dict with keys:
          - ``dry_run`` (bool)
          - ``row_found`` (bool) — whether the row was present in the collab
          - ``views_affected`` (list[str]) — view IDs where the row was removed
          - ``view_row_counts`` (dict) — per-view before/after row counts
          - ``delta_update_bytes`` (int) — size of the incremental update
          - ``server_status`` (int | None) — HTTP status from web-update (live only)
          - ``collab_verified`` (bool | None) — post-delete verification (live only)
          - ``rest_row_list_verified`` (bool | None) — whether row list omits the row
            after deletion (live only)
          - ``rest_verified`` (bool | None) — backward-compatible alias for
            ``rest_row_list_verified``
          - ``row_detail_still_resolvable`` (bool | None) — whether AppFlowy still
            returns row detail by explicit id after row-order removal (live only)
        """
        from appflowy_mcp_toolkit.collab.collab_delete import (
            CollabHelperError,
            allow_collab_writes,
            invoke_yjs_delete,
        )

        if not dry_run:
            self._require_writes_enabled()
            if not allow_collab_writes():
                raise AppFlowyError(
                    "Collab writes are disabled. "
                    "Set APPFLOWY_ALLOW_COLLAB_WRITES=true to enable experimental "
                    "Yjs-based row deletion."
                )

        # Step 1: fetch binary collab state
        binary = self.get_binary_collab(workspace_id, database_id, collab_type="Database")
        doc_state: list[int] = binary.get("doc_state", [])
        if not doc_state:
            raise AppFlowyError(
                "Binary collab returned empty doc_state; cannot compute delete delta."
            )

        # Step 2: invoke Yjs helper (pure, no network)
        try:
            helper_result = invoke_yjs_delete(doc_state, row_id)
        except CollabHelperError as exc:
            raise AppFlowyError(str(exc)) from exc

        summary: dict[str, Any] = {
            "dry_run": dry_run,
            "row_found": helper_result["row_found"],
            "views_affected": helper_result["views_affected"],
            "view_row_counts": helper_result["view_row_counts"],
            "delta_update_bytes": len(helper_result["delta_update"]),
        }

        if not helper_result["row_found"]:
            summary["warning"] = (
                "Row not found in binary collab row_orders. "
                "The row may be visible via REST but not yet synced to the collab state. "
                "No update was posted."
            )
            return summary

        if dry_run:
            return summary

        # Step 3: POST incremental delta to web-update
        post_data = self.request(
            "POST",
            f"/api/workspace/v1/{workspace_id}/collab/{database_id}/web-update",
            json={
                "doc_state": helper_result["delta_update"],
                "collab_type": _collab_type_int("Database"),
            },
        )
        summary["server_status"] = post_data.get("code")

        # Step 4: post-delete verification
        try:
            orders_after = self.get_database_row_orders(workspace_id, database_id)
            still_present = any(row_id in v["row_orders"] for v in orders_after)
            summary["collab_verified"] = not still_present
        except AppFlowyError:
            summary["collab_verified"] = None

        try:
            rest_rows = self.list_database_row_ids(workspace_id, database_id)
            rest_row_list_verified = not any(r.get("id") == row_id for r in rest_rows)
            summary["rest_row_list_verified"] = rest_row_list_verified
            # Backward-compatible key kept for callers that already consume the
            # experimental output. It means "absent from the row list", not
            # necessarily "row collab object was physically purged".
            summary["rest_verified"] = rest_row_list_verified
        except AppFlowyError:
            summary["rest_row_list_verified"] = None
            summary["rest_verified"] = None

        try:
            row_detail = self.get_database_rows(workspace_id, database_id, [row_id])
            summary["row_detail_still_resolvable"] = bool(row_detail)
        except AppFlowyError:
            summary["row_detail_still_resolvable"] = None

        return summary

    def reorder_database_row_collab(
        self,
        workspace_id: str,
        database_id: str,
        view_id: str,
        row_id: str,
        *,
        before_row_id: str | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Reorder a row/card inside a board/grid view via Yjs collab mutation.

        Moves ``row_id`` to the position immediately before ``before_row_id``
        in ``view_id``'s ``row_orders``.  Pass ``before_row_id=None`` to
        move the row to the end of the view.

        Dry-run by default.  Live writes require both
        ``APPFLOWY_ALLOW_WRITES=true`` and
        ``APPFLOWY_ALLOW_COLLAB_WRITES=true``.

        Parameters
        ----------
        workspace_id:
            AppFlowy workspace UUID string.
        database_id:
            AppFlowy database UUID string (the collab object that owns views).
        view_id:
            The specific database view whose row order to change.
        row_id:
            The row to reposition.
        before_row_id:
            Insert the row before this row id.  ``None`` appends to the end.
        dry_run:
            If ``True`` (default), compute and return the mutation summary
            without posting to the server.

        Returns
        -------
        dict with keys: ``dry_run``, ``moved``, ``from_index``, ``to_index``,
        ``delta_update_bytes``, ``server_status`` (live only).
        """
        from appflowy_mcp_toolkit.collab.collab_delete import (
            allow_collab_writes,
            invoke_yjs_reorder_row,
        )

        if not dry_run:
            self._require_writes_enabled()
            if not allow_collab_writes():
                raise AppFlowyError(
                    "APPFLOWY_ALLOW_COLLAB_WRITES is not set. "
                    "Set APPFLOWY_ALLOW_COLLAB_WRITES=true to enable collab writes."
                )

        binary = self.get_binary_collab(workspace_id, database_id, collab_type="Database")
        doc_state: list[int] = binary.get("doc_state", [])
        if not doc_state:
            raise AppFlowyError(
                "Binary Database collab returned empty doc_state; cannot compute reorder delta."
            )
        result = invoke_yjs_reorder_row(
            doc_state,
            view_id=view_id,
            row_id=row_id,
            before_row_id=before_row_id,
        )

        summary: dict[str, Any] = {
            "dry_run": dry_run,
            "moved": result.get("moved"),
            "from_index": result.get("from_index"),
            "to_index": result.get("to_index"),
            "delta_update_bytes": len(result.get("delta_update", [])),
            "server_status": None,
        }

        if not dry_run:
            post_data = self.request(
                "POST",
                f"/api/workspace/v1/{workspace_id}/collab/{database_id}/web-update",
                json={
                    "doc_state": result["delta_update"],
                    "collab_type": _collab_type_int("Database"),
                },
            )
            summary["server_status"] = post_data.get("code")

        return summary

    def reorder_database_column_collab(
        self,
        workspace_id: str,
        database_id: str,
        view_id: str,
        field_id: str,
        group_id: str,
        *,
        before_group_id: str | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Reorder a board column (group) inside a database view via Yjs collab mutation.

        Moves the column identified by ``group_id`` (a Status option id for
        Status-grouped boards) to the position immediately before
        ``before_group_id``.  Pass ``before_group_id=None`` to move the
        column to the end.

        ``field_id`` must be the id of the field used to group the board view
        (typically the Status field id, obtainable from
        :meth:`list_database_fields`).

        Dry-run by default.  Live writes require both
        ``APPFLOWY_ALLOW_WRITES=true`` and
        ``APPFLOWY_ALLOW_COLLAB_WRITES=true``.

        Parameters
        ----------
        workspace_id:
            AppFlowy workspace UUID string.
        database_id:
            AppFlowy database UUID string.
        view_id:
            The specific database view whose column order to change.
        field_id:
            The grouping field id (e.g. Status field id).
        group_id:
            The column to reposition — this is the select option id.
        before_group_id:
            Insert the column before this group id.  ``None`` appends.
        dry_run:
            If ``True`` (default), compute and return the mutation summary
            without posting to the server.

        Returns
        -------
        dict with keys: ``dry_run``, ``moved``, ``from_index``, ``to_index``,
        ``delta_update_bytes``, ``server_status`` (live only).
        """
        from appflowy_mcp_toolkit.collab.collab_delete import (
            allow_collab_writes,
            invoke_yjs_reorder_column,
        )

        if not dry_run:
            self._require_writes_enabled()
            if not allow_collab_writes():
                raise AppFlowyError(
                    "APPFLOWY_ALLOW_COLLAB_WRITES is not set. "
                    "Set APPFLOWY_ALLOW_COLLAB_WRITES=true to enable collab writes."
                )

        binary = self.get_binary_collab(workspace_id, database_id, collab_type="Database")
        doc_state: list[int] = binary.get("doc_state", [])
        if not doc_state:
            raise AppFlowyError(
                "Binary Database collab returned empty doc_state; cannot compute reorder delta."
            )
        result = invoke_yjs_reorder_column(
            doc_state,
            view_id=view_id,
            field_id=field_id,
            group_id=group_id,
            before_group_id=before_group_id,
        )

        summary: dict[str, Any] = {
            "dry_run": dry_run,
            "moved": result.get("moved"),
            "from_index": result.get("from_index"),
            "to_index": result.get("to_index"),
            "delta_update_bytes": len(result.get("delta_update", [])),
            "server_status": None,
        }

        if not dry_run:
            post_data = self.request(
                "POST",
                f"/api/workspace/v1/{workspace_id}/collab/{database_id}/web-update",
                json={
                    "doc_state": result["delta_update"],
                    "collab_type": _collab_type_int("Database"),
                },
            )
            summary["server_status"] = post_data.get("code")

        return summary
