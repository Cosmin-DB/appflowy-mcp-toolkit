from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import httpx

from .blob_diff import decode_database_blob_diff_response, encode_database_blob_diff_request
from .config import AppFlowyConfig
from .errors import AppFlowyError, AppFlowySchemaError, classify_http_error
from .typed_fields import build_cells


class AppFlowyClient:
    """Small REST client for AppFlowy Cloud/self-hosted API."""

    def __init__(
        self, config: AppFlowyConfig | None = None, *, http_client: httpx.Client | None = None
    ):
        self.config = config or AppFlowyConfig.from_env()
        self._client = http_client or httpx.Client(timeout=self.config.timeout_seconds)
        self._owns_client = http_client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> AppFlowyClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

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
        url = self._url(path)
        headers = {"Accept": "application/json"}
        if require_auth:
            headers["Authorization"] = f"Bearer {self.config.require_token()}"
        response = self._client.request(method, url, headers=headers, params=params, json=json)
        if response.status_code == 401 and _retry_refresh and self.config.refresh_token:
            self._refresh_access_token()
            return self.request(
                method,
                path,
                params=params,
                json=json,
                require_auth=require_auth,
                _retry_refresh=False,
            )
        if response.status_code >= 400:
            raise classify_http_error(
                response.status_code,
                self._safe_error_message(response),
                retry_after=response.headers.get("retry-after"),
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise AppFlowySchemaError("AppFlowy returned non-JSON response") from exc
        if not isinstance(data, dict):
            raise AppFlowySchemaError("AppFlowy response was not a JSON object", payload=data)
        return data

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
        url = self._url(path)
        headers = {"Accept": "application/octet-stream", "Content-Type": content_type}
        if require_auth:
            headers["Authorization"] = f"Bearer {self.config.require_token()}"
        response = self._client.request(method, url, headers=headers, content=content)
        if response.status_code == 401 and _retry_refresh and self.config.refresh_token:
            self._refresh_access_token()
            return self.request_bytes(
                method,
                path,
                content=content,
                content_type=content_type,
                require_auth=require_auth,
                _retry_refresh=False,
            )
        if response.status_code >= 400:
            raise classify_http_error(
                response.status_code,
                self._safe_error_message(response),
                retry_after=response.headers.get("retry-after"),
            )
        return response.content

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

    def get_file_storage_usage(self, workspace_id: str) -> dict[str, Any]:
        data = self.request("GET", f"/api/file_storage/{workspace_id}/usage")
        usage = self._extract_data(data)
        if not isinstance(usage, dict):
            raise AppFlowySchemaError("Expected AppFlowy file-storage usage response", payload=data)
        return usage

    def list_file_storage_blobs(self, workspace_id: str) -> list[dict[str, Any]]:
        data = self.request("GET", f"/api/file_storage/{workspace_id}/blobs")
        return self._extract_list(data)

    def get_file_metadata(self, workspace_id: str, file_id: str) -> dict[str, Any]:
        data = self.request("GET", f"/api/file_storage/{workspace_id}/metadata/{file_id}")
        metadata = self._extract_data(data)
        if not isinstance(metadata, dict):
            raise AppFlowySchemaError("Expected AppFlowy file metadata response", payload=data)
        return metadata

    def get_file_metadata_v1(
        self,
        workspace_id: str,
        parent_dir: str,
        file_id: str,
    ) -> dict[str, Any]:
        data = self.request(
            "GET",
            f"/api/file_storage/{workspace_id}/v1/metadata/{parent_dir}/{file_id}",
        )
        metadata = self._extract_data(data)
        if not isinstance(metadata, dict):
            raise AppFlowySchemaError("Expected AppFlowy v1 file metadata response", payload=data)
        return metadata

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

    def get_folder(
        self,
        workspace_id: str,
        *,
        depth: int | None = None,
        root_view_id: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if depth is not None:
            params["depth"] = depth
        if root_view_id:
            params["root_view_id"] = root_view_id
        data = self.request("GET", f"/api/workspace/{workspace_id}/folder", params=params or None)
        return self._extract_data(data)

    def create_folder_view(
        self,
        workspace_id: str,
        *,
        parent_view_id: str,
        layout: int = 0,
        name: str | None = None,
        view_id: str | None = None,
        database_id: str | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "parent_view_id": parent_view_id,
            "layout": layout,
        }
        if name is not None:
            payload["name"] = name
        if view_id is not None:
            payload["view_id"] = view_id
        if database_id is not None:
            payload["database_id"] = database_id
        path = f"/api/workspace/{workspace_id}/folder-view"
        if dry_run:
            return {"dry_run": True, "method": "POST", "path": path, "json": payload}
        self._require_writes_enabled()
        return self.request("POST", path, json=payload)

    def get_page_view(self, workspace_id: str, view_id: str) -> dict[str, Any]:
        data = self.request("GET", f"/api/workspace/{workspace_id}/page-view/{view_id}")
        page = self._extract_data(data)
        if not isinstance(page, dict):
            raise AppFlowySchemaError("Expected AppFlowy page-view response", payload=data)
        return page

    def create_page_view(
        self,
        workspace_id: str,
        *,
        parent_view_id: str,
        layout: int = 0,
        name: str | None = None,
        page_data: dict[str, Any] | None = None,
        view_id: str | None = None,
        collab_id: str | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "parent_view_id": parent_view_id,
            "layout": layout,
        }
        if name is not None:
            payload["name"] = name
        if page_data is not None:
            payload["page_data"] = page_data
        if view_id is not None:
            payload["view_id"] = view_id
        if collab_id is not None:
            payload["collab_id"] = collab_id
        path = f"/api/workspace/{workspace_id}/page-view"
        if dry_run:
            return {"dry_run": True, "method": "POST", "path": path, "json": payload}
        self._require_writes_enabled()
        return self.request("POST", path, json=payload)

    def update_page_view(
        self,
        workspace_id: str,
        view_id: str,
        *,
        name: str,
        icon: dict[str, Any] | None = None,
        is_locked: bool | None = None,
        extra: dict[str, Any] | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": name}
        if icon is not None:
            payload["icon"] = icon
        if is_locked is not None:
            payload["is_locked"] = is_locked
        if extra is not None:
            payload["extra"] = extra
        path = f"/api/workspace/{workspace_id}/page-view/{view_id}"
        if dry_run:
            return {"dry_run": True, "method": "PATCH", "path": path, "json": payload}
        self._require_writes_enabled()
        return self.request("PATCH", path, json=payload)

    def update_page_name(
        self,
        workspace_id: str,
        view_id: str,
        *,
        name: str,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        payload = {"name": name}
        path = f"/api/workspace/{workspace_id}/page-view/{view_id}/update-name"
        if dry_run:
            return {"dry_run": True, "method": "POST", "path": path, "json": payload}
        self._require_writes_enabled()
        return self.request("POST", path, json=payload)

    def favorite_page_view(
        self,
        workspace_id: str,
        view_id: str,
        *,
        is_favorite: bool,
        is_pinned: bool = False,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        payload = {"is_favorite": is_favorite, "is_pinned": is_pinned}
        path = f"/api/workspace/{workspace_id}/page-view/{view_id}/favorite"
        if dry_run:
            return {"dry_run": True, "method": "POST", "path": path, "json": payload}
        self._require_writes_enabled()
        return self.request("POST", path, json=payload)

    def remove_page_icon(
        self,
        workspace_id: str,
        view_id: str,
        *,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        path = f"/api/workspace/{workspace_id}/page-view/{view_id}/remove-icon"
        if dry_run:
            return {"dry_run": True, "method": "POST", "path": path, "json": {}}
        self._require_writes_enabled()
        return self.request("POST", path, json={})

    def append_blocks_to_page(
        self,
        workspace_id: str,
        view_id: str,
        *,
        blocks: list[dict[str, Any]],
        dry_run: bool = True,
    ) -> dict[str, Any]:
        payload = {"blocks": blocks}
        path = f"/api/workspace/{workspace_id}/page-view/{view_id}/append-block"
        if dry_run:
            return {"dry_run": True, "method": "POST", "path": path, "json": payload}
        self._require_writes_enabled()
        return self.request("POST", path, json=payload)

    def move_page_view(
        self,
        workspace_id: str,
        view_id: str,
        *,
        new_parent_view_id: str,
        prev_view_id: str | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"new_parent_view_id": new_parent_view_id}
        if prev_view_id is not None:
            payload["prev_view_id"] = prev_view_id
        path = f"/api/workspace/{workspace_id}/page-view/{view_id}/move"
        if dry_run:
            return {"dry_run": True, "method": "POST", "path": path, "json": payload}
        self._require_writes_enabled()
        return self.request("POST", path, json=payload)

    def reorder_favorite_page_view(
        self,
        workspace_id: str,
        view_id: str,
        *,
        prev_view_id: str | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if prev_view_id is not None:
            payload["prev_view_id"] = prev_view_id
        path = f"/api/workspace/{workspace_id}/page-view/{view_id}/reorder-favorite"
        if dry_run:
            return {"dry_run": True, "method": "POST", "path": path, "json": payload}
        self._require_writes_enabled()
        return self.request("POST", path, json=payload)

    def duplicate_page_view(
        self,
        workspace_id: str,
        view_id: str,
        *,
        suffix: str | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if suffix is not None:
            payload["suffix"] = suffix
        path = f"/api/workspace/{workspace_id}/page-view/{view_id}/duplicate"
        if dry_run:
            return {"dry_run": True, "method": "POST", "path": path, "json": payload}
        self._require_writes_enabled()
        return self.request("POST", path, json=payload)

    def create_page_database_view(
        self,
        workspace_id: str,
        view_id: str,
        *,
        layout: int,
        name: str | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"layout": layout}
        if name is not None:
            payload["name"] = name
        path = f"/api/workspace/{workspace_id}/page-view/{view_id}/database-view"
        if dry_run:
            return {"dry_run": True, "method": "POST", "path": path, "json": payload}
        self._require_writes_enabled()
        return self.request("POST", path, json=payload)

    def move_page_view_to_trash(
        self,
        workspace_id: str,
        view_id: str,
        *,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        path = f"/api/workspace/{workspace_id}/page-view/{view_id}/move-to-trash"
        if dry_run:
            return {"dry_run": True, "method": "POST", "path": path, "json": {}}
        self._require_writes_enabled()
        return self.request("POST", path, json={})

    def restore_page_view_from_trash(
        self,
        workspace_id: str,
        view_id: str,
        *,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        path = f"/api/workspace/{workspace_id}/page-view/{view_id}/restore-from-trash"
        if dry_run:
            return {"dry_run": True, "method": "POST", "path": path, "json": {}}
        self._require_writes_enabled()
        return self.request("POST", path, json={})

    def delete_page_view_from_trash(
        self,
        workspace_id: str,
        view_id: str,
        *,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        path = f"/api/workspace/{workspace_id}/trash/{view_id}"
        if dry_run:
            return {"dry_run": True, "method": "DELETE", "path": path}
        self._require_writes_enabled()
        return self.request("DELETE", path)

    def add_recent_pages(
        self,
        workspace_id: str,
        recent_view_ids: list[str],
        *,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        payload = {"recent_view_ids": recent_view_ids}
        path = f"/api/workspace/{workspace_id}/add-recent-pages"
        if dry_run:
            return {"dry_run": True, "method": "POST", "path": path, "json": payload}
        self._require_writes_enabled()
        return self.request("POST", path, json=payload)

    def restore_all_pages_from_trash(
        self,
        workspace_id: str,
        *,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        path = f"/api/workspace/{workspace_id}/restore-all-pages-from-trash"
        if dry_run:
            return {"dry_run": True, "method": "POST", "path": path, "json": {}}
        self._require_writes_enabled()
        return self.request("POST", path, json={})

    def delete_all_pages_from_trash(
        self,
        workspace_id: str,
        *,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        path = f"/api/workspace/{workspace_id}/delete-all-pages-from-trash"
        if dry_run:
            return {"dry_run": True, "method": "POST", "path": path, "json": {}}
        self._require_writes_enabled()
        return self.request("POST", path, json={})

    def list_recent_views(self, workspace_id: str) -> list[dict[str, Any]]:
        data = self.request("GET", f"/api/workspace/{workspace_id}/recent")
        return self._extract_list(data)

    def list_favorite_views(self, workspace_id: str) -> list[dict[str, Any]]:
        data = self.request("GET", f"/api/workspace/{workspace_id}/favorite")
        return self._extract_list(data)

    def list_trash_views(self, workspace_id: str) -> list[dict[str, Any]]:
        data = self.request("GET", f"/api/workspace/{workspace_id}/trash")
        return self._extract_list(data)

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
        """Create an MCP-managed task using the public task-facing API."""
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

    # ------------------------------------------------------------------
    # Collab inspector (read-only)
    # ------------------------------------------------------------------

    def get_collab_json(
        self,
        workspace_id: str,
        object_id: str,
        *,
        collab_type: str | int = "Database",
    ) -> dict[str, Any]:
        """Fetch a collab document as JSON.

        Uses ``GET /api/workspace/v1/{workspace_id}/collab/{object_id}/json``.

        ``collab_type`` can be a well-known string name or an explicit integer::

            "Document" = 0, "Database" = 1, "WorkspaceDatabase" = 2,
            "Folder" = 3, "DatabaseRow" = 4, "UserAwareness" = 5

        The server requires the integer form; string names are resolved
        automatically.
        """
        data = self.request(
            "GET",
            f"/api/workspace/v1/{workspace_id}/collab/{object_id}/json",
            params={"collab_type": _collab_type_int(collab_type)},
        )
        return self._extract_data(data)

    def get_database_row_orders(
        self,
        workspace_id: str,
        database_id: str,
    ) -> list[dict[str, Any]]:
        """Return per-view row orders extracted from the database collab document.

        Each entry has ``view_id`` and ``row_orders`` (list of row-id strings).
        Returns an empty list if the collab document has no recognisable views.
        """
        collab = self.get_collab_json(workspace_id, database_id, collab_type="Database")
        return _extract_row_orders(collab)

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

    # ------------------------------------------------------------------
    # Experimental: Yjs-based collab row delete (M6.3)
    # ------------------------------------------------------------------

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

    def health_check(self) -> dict[str, Any]:
        try:
            self.request("GET", "/api/workspace")
        except AppFlowyError as exc:
            return {"ok": False, "status_code": exc.status_code, "message": str(exc)}
        except httpx.TransportError as exc:
            return {"ok": False, "status_code": None, "message": f"Connection error: {exc}"}
        return {"ok": True, "base_url": self.config.base_url}

    def _refresh_access_token(self) -> None:
        response = self.request(
            "POST",
            "/gotrue/token",
            params={"grant_type": "refresh_token"},
            json={"grant_type": "refresh_token", "refresh_token": self.config.refresh_token},
            require_auth=False,
            _retry_refresh=False,
        )
        token = response.get("access_token")
        if not isinstance(token, str) or not token:
            raise AppFlowySchemaError("Refresh response did not include access_token")
        self.config = AppFlowyConfig(
            base_url=self.config.base_url,
            access_token=token,
            refresh_token=response.get("refresh_token") or self.config.refresh_token,
            timeout_seconds=self.config.timeout_seconds,
            allow_writes=self.config.allow_writes,
        )

    def _url(self, path: str) -> str:
        return f"{self.config.base_url}/{path.lstrip('/')}"

    def _require_writes_enabled(self) -> None:
        if not self.config.allow_writes:
            raise AppFlowyError(
                "Writes are disabled. Set APPFLOWY_ALLOW_WRITES=true or use dry_run=True."
            )

    @staticmethod
    def _extract_data(data: dict[str, Any]) -> Any:
        return data.get("data", data)

    @classmethod
    def _extract_list(cls, data: dict[str, Any]) -> list[dict[str, Any]]:
        payload = cls._extract_data(data)
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            for key in ("items", "rows", "databases", "workspaces", "members", "blobs", "views"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
        raise AppFlowySchemaError("Expected AppFlowy list response", payload=data)

    @staticmethod
    def _safe_error_message(response: httpx.Response) -> str:
        try:
            payload = response.json()
            if isinstance(payload, dict):
                message = payload.get("message") or payload.get("error")
                if isinstance(message, str):
                    return f"AppFlowy API error {response.status_code}: {message}"
        except ValueError:
            pass
        return f"AppFlowy API error {response.status_code}"


def _collab_type_int(collab_type: str | int) -> int:
    """Resolve a collab type name, integer, or decimal numeric string to the
    integer the server requires.

    The AppFlowy Cloud ``/json`` endpoint deserialises ``collab_type`` as an
    integer.  Passing a string such as ``"Database"`` results in a 400 error.

    Accepted forms:
    - ``int``: forwarded as-is (e.g. ``1``)
    - decimal numeric string: parsed as int (e.g. ``"1"`` → ``1``)
    - known name string: mapped to int (e.g. ``"Database"`` → ``1``)

    Known mappings (from ``collab_entity::CollabType``):
    ``Document=0, Database=1, WorkspaceDatabase=2, Folder=3,
    DatabaseRow=4, UserAwareness=5``.
    """
    if isinstance(collab_type, int):
        return collab_type
    if collab_type.isdigit():
        return int(collab_type)
    _COLLAB_TYPE_MAP: dict[str, int] = {
        "Document": 0,
        "Database": 1,
        "WorkspaceDatabase": 2,
        "Folder": 3,
        "DatabaseRow": 4,
        "UserAwareness": 5,
    }
    resolved = _COLLAB_TYPE_MAP.get(collab_type)
    if resolved is None:
        raise AppFlowyError(
            f"Unknown collab_type name {collab_type!r}. "
            f"Pass an integer, a decimal string, or one of: {list(_COLLAB_TYPE_MAP)}"
        )
    return resolved


def _extract_row_id(create_result: dict[str, Any]) -> str | None:
    data = create_result.get("data")
    if isinstance(data, str) and data:
        return data
    if isinstance(data, dict):
        for key in ("id", "row_id"):
            value = data.get(key)
            if isinstance(value, str) and value:
                return value
    for key in ("id", "row_id"):
        value = create_result.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _extract_row_orders(collab: Any) -> list[dict[str, Any]]:
    """Extract per-view row orders from a database collab JSON payload.

    The AppFlowy Cloud ``/json`` endpoint returns (after ``_extract_data``) a
    dict whose shape depends on the server version:

    **Observed AppFlowy response shape** (2026-05):

    .. code-block:: json

        {"collab": {"database": {"views": {"<view_id>": {"row_orders": [...]}}}}}

    **Flat fixture shape** (used in unit tests / earlier schema):

    .. code-block:: json

        {"views": {"<view_id>": {"row_orders": [...]}}}

    **Inline-views fallback**:

    .. code-block:: json

        {"database_inline_views": {"<view_id>": {"row_orders": [...]}}}

    This helper tries all known locations and returns the first non-empty match.
    ``row_orders`` entries may be plain strings or ``{"id": "..."}`` dicts;
    both are normalised to strings.

    Returns a list of dicts::

        [{"view_id": "<id>", "row_orders": ["<row_id>", ...]}, ...]
    """
    if not isinstance(collab, dict):
        return []

    def _views_to_results(views: Any) -> list[dict[str, Any]]:
        if not isinstance(views, dict):
            return []
        out = []
        for view_id, view_data in views.items():
            if not isinstance(view_data, dict):
                continue
            row_orders = _coerce_row_orders(view_data.get("row_orders"))
            out.append({"view_id": str(view_id), "row_orders": row_orders})
        return out

    # 1. Live shape: collab.database.views
    nested_collab = collab.get("collab")
    if isinstance(nested_collab, dict):
        db = nested_collab.get("database")
        if isinstance(db, dict):
            results = _views_to_results(db.get("views"))
            if results:
                return results

    # 2. Flat shape: top-level "views" key
    results = _views_to_results(collab.get("views"))
    if results:
        return results

    # 3. Inline-views fallback
    for key in ("database_inline_views", "inline_views"):
        results = _views_to_results(collab.get(key))
        if results:
            return results

    return []


def _coerce_row_orders(raw: Any) -> list[str]:
    """Normalise row_orders to a flat list of row-id strings.

    AppFlowy may encode row_orders as:
    - a list of strings: ["row_id_1", ...]
    - a list of dicts: [{"id": "row_id_1"}, ...]
    - absent / other: return []
    """
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            row_id = item.get("id")
            if isinstance(row_id, str):
                out.append(row_id)
    return out
