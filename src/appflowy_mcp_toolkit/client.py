from __future__ import annotations

import mimetypes
import secrets
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from .blob_diff import decode_database_blob_diff_response, encode_database_blob_diff_request
from .config import AppFlowyConfig
from .errors import AppFlowyError, AppFlowySchemaError, classify_http_error
from .typed_fields import build_cells, build_collab_cell_updates


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
        url = self._url(path)
        headers = {"Accept": "application/json", "Content-Type": content_type}
        if require_auth:
            headers["Authorization"] = f"Bearer {self.config.require_token()}"
        response = self._client.request(method, url, headers=headers, content=content)
        if response.status_code == 401 and _retry_refresh and self.config.refresh_token:
            self._refresh_access_token()
            return self.request_content_json(
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
        try:
            data = response.json()
        except ValueError as exc:
            raise AppFlowySchemaError("AppFlowy returned non-JSON response") from exc
        if not isinstance(data, dict):
            raise AppFlowySchemaError("AppFlowy response was not a JSON object", payload=data)
        return data

    def request_bytes_with_headers(
        self,
        method: str,
        path: str,
        *,
        require_auth: bool = True,
        _retry_refresh: bool = True,
    ) -> tuple[str, bytes]:
        url = self._url(path)
        headers = {"Accept": "application/octet-stream"}
        if require_auth:
            headers["Authorization"] = f"Bearer {self.config.require_token()}"
        response = self._client.request(method, url, headers=headers)
        if response.status_code == 401 and _retry_refresh and self.config.refresh_token:
            self._refresh_access_token()
            return self.request_bytes_with_headers(
                method,
                path,
                require_auth=require_auth,
                _retry_refresh=False,
            )
        if response.status_code >= 400:
            raise classify_http_error(
                response.status_code,
                self._safe_error_message(response),
                retry_after=response.headers.get("retry-after"),
            )
        return response.headers.get("content-type", "application/octet-stream"), response.content

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

    def get_workspace_publish_namespace(self, workspace_id: str) -> str:
        data = self.request(
            "GET",
            f"/api/workspace/{workspace_id}/publish-namespace",
            require_auth=False,
        )
        namespace = self._extract_data(data)
        if not isinstance(namespace, str):
            raise AppFlowySchemaError(
                "Expected AppFlowy publish namespace response",
                payload=data,
            )
        return namespace

    def get_workspace_publish_default(self, workspace_id: str) -> dict[str, Any]:
        data = self.request(
            "GET",
            f"/api/workspace/{workspace_id}/publish-default",
            require_auth=False,
        )
        default_info = self._extract_data(data)
        if not isinstance(default_info, dict):
            raise AppFlowySchemaError(
                "Expected AppFlowy default published view response",
                payload=data,
            )
        return default_info

    def list_published_pages(self, workspace_id: str) -> list[dict[str, Any]]:
        data = self.request(
            "GET",
            f"/api/workspace/{workspace_id}/published-info",
            require_auth=False,
        )
        return self._extract_list(data)

    def get_published_page_info(
        self,
        view_id: str,
        *,
        include_unpublished: bool = False,
    ) -> dict[str, Any]:
        prefix = "/api/workspace/v1" if include_unpublished else "/api/workspace"
        data = self.request(
            "GET",
            f"{prefix}/published-info/{view_id}",
            require_auth=False,
        )
        publish_info = self._extract_data(data)
        if not isinstance(publish_info, dict):
            raise AppFlowySchemaError(
                "Expected AppFlowy published page info response",
                payload=data,
            )
        return publish_info

    def publish_page(
        self,
        workspace_id: str,
        view_id: str,
        *,
        publish_name: str | None = None,
        visible_database_view_ids: list[str] | None = None,
        comments_enabled: bool | None = None,
        duplicate_enabled: bool | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Publish an AppFlowy page view.

        Route confirmed in AppFlowy-Cloud src/api/workspace.rs:
          POST /api/workspace/{workspace_id}/page-view/{view_id}/publish

        Requires APPFLOWY_ALLOW_WRITES=true AND APPFLOWY_ALLOW_PUBLISH_WRITES=true
        for live execution.  Dry-run (default) returns method/path/payload only.
        """
        path = f"/api/workspace/{workspace_id}/page-view/{view_id}/publish"
        payload: dict[str, Any] = {}
        if publish_name is not None:
            payload["publish_name"] = publish_name
        if visible_database_view_ids is not None:
            payload["visible_database_view_ids"] = visible_database_view_ids
        if comments_enabled is not None:
            payload["comments_enabled"] = comments_enabled
        if duplicate_enabled is not None:
            payload["duplicate_enabled"] = duplicate_enabled
        if dry_run:
            return {"dry_run": True, "method": "POST", "path": path, "json": payload}
        self._require_publish_writes_enabled()
        data = self.request("POST", path, json=payload)
        return {"path": path, "response": data}

    def unpublish_page(
        self,
        workspace_id: str,
        view_id: str,
        *,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Unpublish an AppFlowy page view.

        Route confirmed in AppFlowy-Cloud src/api/workspace.rs:
          POST /api/workspace/{workspace_id}/page-view/{view_id}/unpublish

        Requires APPFLOWY_ALLOW_WRITES=true AND APPFLOWY_ALLOW_PUBLISH_WRITES=true
        for live execution.  Dry-run (default) returns method/path summary.
        """
        path = f"/api/workspace/{workspace_id}/page-view/{view_id}/unpublish"
        if dry_run:
            return {"dry_run": True, "method": "POST", "path": path}
        self._require_publish_writes_enabled()
        data = self.request("POST", path)
        return {"path": path, "response": data}

    def duplicate_published_page(
        self,
        workspace_id: str,
        *,
        published_view_id: str,
        dest_view_id: str,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Duplicate a published AppFlowy page/template into the workspace.

        Route confirmed in AppFlowy-Cloud src/api/workspace.rs:
          POST /api/workspace/{workspace_id}/published-duplicate
        Payload: { published_view_id, dest_view_id }
        Response: { view_id: <root_view_id_for_duplicate> }

        This writes to the user's own workspace and therefore requires only
        APPFLOWY_ALLOW_WRITES=true (not the publish gate).
        Dry-run (default) returns method/path/payload summary without network call.
        """
        path = f"/api/workspace/{workspace_id}/published-duplicate"
        payload: dict[str, Any] = {
            "published_view_id": published_view_id,
            "dest_view_id": dest_view_id,
        }
        if dry_run:
            return {"dry_run": True, "method": "POST", "path": path, "json": payload}
        self._require_writes_enabled()
        data = self.request("POST", path, json=payload)
        result = self._extract_data(data)
        if not isinstance(result, dict):
            raise AppFlowySchemaError(
                "Expected DuplicatePublishedPageResponse from AppFlowy", payload=data
            )
        return result

    def instantiate_template(
        self,
        workspace_id: str,
        *,
        template_view_id: str,
        dest_view_id: str,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Instantiate a published AppFlowy template into a destination view.

        Friendly alias for duplicate_published_page that uses template_view_id
        as the published_view_id.  Only works for pages/templates that are
        already published on AppFlowy; arbitrary unpublished templates are not
        supported via this route.

        Requires APPFLOWY_ALLOW_WRITES=true for live execution.
        """
        return self.duplicate_published_page(
            workspace_id,
            published_view_id=template_view_id,
            dest_view_id=dest_view_id,
            dry_run=dry_run,
        )

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

    def upload_file_blob_v1(
        self,
        workspace_id: str,
        parent_dir: str,
        *,
        content: bytes,
        content_type: str = "application/octet-stream",
        dry_run: bool = True,
    ) -> dict[str, Any]:
        encoded_parent_dir = quote(parent_dir, safe="")
        path = f"/api/file_storage/{workspace_id}/v1/blob/{encoded_parent_dir}"
        if dry_run:
            return {
                "dry_run": True,
                "method": "PUT",
                "path": path,
                "content_type": content_type,
                "content_length": len(content),
            }
        self._require_writes_enabled()
        data = self.request_content_json("PUT", path, content=content, content_type=content_type)
        payload = self._extract_data(data)
        if not isinstance(payload, dict):
            raise AppFlowySchemaError("Expected AppFlowy v1 file upload response", payload=data)
        file_id = payload.get("file_id")
        if not isinstance(file_id, str) or not file_id:
            raise AppFlowySchemaError(
                "AppFlowy v1 upload response did not include file_id", payload=data
            )
        return {
            **payload,
            "workspace_id": workspace_id,
            "parent_dir": parent_dir,
            "url": self.file_blob_url_v1(workspace_id, parent_dir, file_id),
            "content_type": content_type,
            "content_length": len(content),
        }

    def upload_local_file_blob_v1(
        self,
        workspace_id: str,
        parent_dir: str,
        file_path: str | Path,
        *,
        content_type: str | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        path = Path(file_path)
        guessed_type = (
            content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        )
        content = path.read_bytes()
        return self.upload_file_blob_v1(
            workspace_id,
            parent_dir,
            content=content,
            content_type=guessed_type,
            dry_run=dry_run,
        )

    def get_file_blob_v1(
        self, workspace_id: str, parent_dir: str, file_id: str
    ) -> tuple[str, bytes]:
        encoded_parent_dir = quote(parent_dir, safe="")
        return self.request_bytes_with_headers(
            "GET",
            f"/api/file_storage/{workspace_id}/v1/blob/{encoded_parent_dir}/{file_id}",
        )

    def delete_file_blob_v1(
        self,
        workspace_id: str,
        parent_dir: str,
        file_id: str,
        *,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        encoded_parent_dir = quote(parent_dir, safe="")
        path = f"/api/file_storage/{workspace_id}/v1/blob/{encoded_parent_dir}/{file_id}"
        if dry_run:
            return {"dry_run": True, "method": "DELETE", "path": path}
        self._require_writes_enabled()
        self.request("DELETE", path)
        return {
            "deleted": True,
            "workspace_id": workspace_id,
            "parent_dir": parent_dir,
            "file_id": file_id,
        }

    def file_blob_url_v1(self, workspace_id: str, parent_dir: str, file_id: str) -> str:
        encoded_parent_dir = quote(parent_dir, safe="")
        return self._url(f"/api/file_storage/{workspace_id}/v1/blob/{encoded_parent_dir}/{file_id}")

    def upload_file_as_media(
        self,
        workspace_id: str,
        database_id: str,
        file_path: str | Path,
        *,
        name: str | None = None,
        content_type: str | None = None,
        file_type: str | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        path = Path(file_path)
        upload = self.upload_local_file_blob_v1(
            workspace_id,
            database_id,
            path,
            content_type=content_type,
            dry_run=dry_run,
        )
        media_file = {
            "id": upload.get("file_id", ""),
            "name": name or path.name,
            "url": upload.get("url", self.file_blob_url_v1(workspace_id, database_id, "<file_id>")),
            "upload_type": "Cloud",
            "file_type": file_type or self._infer_media_file_type(path),
        }
        return {"upload": upload, "media": media_file}

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

    def append_markdown_to_page(
        self,
        workspace_id: str,
        view_id: str,
        *,
        markdown: str,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Convert Markdown to AppFlowy SerdeBlocks and append to a page.

        Uses the same POST /api/workspace/{workspace_id}/page-view/{view_id}/append-block
        route as append_blocks_to_page.  Converts a safe subset of Markdown
        (paragraphs, headings, bulleted/numbered lists, blockquotes) to blocks
        using the internal markdown_to_blocks converter.

        Supported Markdown: paragraphs, # through ###### headings,
        - / * / + unordered lists, N. ordered lists, > blockquotes.
        Inline rich formatting (bold, italic, code spans, links) is kept as
        plain text; full inline conversion is backlog.

        Raises ValueError / AppFlowySchemaError for empty input.
        Requires APPFLOWY_ALLOW_WRITES=true for live execution.
        """
        from .markdown import markdown_to_blocks

        blocks = markdown_to_blocks(markdown)
        return self.append_blocks_to_page(workspace_id, view_id, blocks=blocks, dry_run=dry_run)

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

    @classmethod
    def _task_candidate(cls, row: dict[str, Any], *, description_text: str) -> dict[str, Any]:
        cells = row.get("cells") if isinstance(row.get("cells"), dict) else {}
        return {
            "row_id": row.get("id") or row.get("row_id"),
            "description": description_text,
            "status": cells.get("Status") if isinstance(cells, dict) else None,
        }

    @classmethod
    def _task_description_text(cls, row: dict[str, Any]) -> str:
        cells = row.get("cells")
        if not isinstance(cells, dict):
            return ""
        return " ".join(cls._flatten_cell_text(cells.get("Description"))).strip()

    @classmethod
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
        collab = self.get_collab_json(workspace_id, database_id, collab_type="Database")
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
        from .collab.collab_delete import (
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
        from .collab.collab_delete import (
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

    # ------------------------------------------------------------------
    # Template-center read-only discovery
    # Routes confirmed in AppFlowy-Cloud src/api/template.rs:
    #   GET /api/template-center/category
    #   GET /api/template-center/category/{category_id}
    #   GET /api/template-center/creator
    #   GET /api/template-center/creator/{creator_id}
    #   GET /api/template-center/template
    #   GET /api/template-center/template/{view_id}
    #   GET /api/template-center/homepage
    # List/get handlers do not require auth (_uuid absent from their
    # Actix signatures), so these reads also work before a user has configured
    # credentials.
    # ------------------------------------------------------------------

    def list_template_categories(
        self,
        *,
        name_contains: str | None = None,
        category_type: int | None = None,
    ) -> list[dict[str, Any]]:
        """List AppFlowy template categories.

        GET /api/template-center/category
        Optional query params: name_contains, category_type (int).
        """
        params: dict[str, Any] = {}
        if name_contains is not None:
            params["name_contains"] = name_contains
        if category_type is not None:
            params["category_type"] = category_type
        data = self.request(
            "GET",
            "/api/template-center/category",
            params=params or None,
            require_auth=False,
        )
        return self._extract_list({"data": data} if not isinstance(data, dict) else data)

    def get_template_category(self, category_id: str) -> dict[str, Any]:
        """Get a single template category by id.

        GET /api/template-center/category/{category_id}
        """
        data = self.request(
            "GET",
            f"/api/template-center/category/{category_id}",
            require_auth=False,
        )
        category = self._extract_data({"data": data} if not isinstance(data, dict) else data)
        if not isinstance(category, dict):
            raise AppFlowySchemaError("Expected AppFlowy template category response", payload=data)
        return category

    def list_template_creators(
        self,
        *,
        name_contains: str | None = None,
    ) -> list[dict[str, Any]]:
        """List AppFlowy template creators.

        GET /api/template-center/creator
        Optional query param: name_contains.
        """
        params: dict[str, Any] = {}
        if name_contains is not None:
            params["name_contains"] = name_contains
        data = self.request(
            "GET",
            "/api/template-center/creator",
            params=params or None,
            require_auth=False,
        )
        return self._extract_list({"data": data} if not isinstance(data, dict) else data)

    def get_template_creator(self, creator_id: str) -> dict[str, Any]:
        """Get a single template creator by id.

        GET /api/template-center/creator/{creator_id}
        """
        data = self.request(
            "GET",
            f"/api/template-center/creator/{creator_id}",
            require_auth=False,
        )
        creator = self._extract_data({"data": data} if not isinstance(data, dict) else data)
        if not isinstance(creator, dict):
            raise AppFlowySchemaError("Expected AppFlowy template creator response", payload=data)
        return creator

    def list_templates(
        self,
        *,
        category_id: str | None = None,
        is_featured: bool | None = None,
        is_new_template: bool | None = None,
        name_contains: str | None = None,
    ) -> list[dict[str, Any]]:
        """List AppFlowy templates.

        GET /api/template-center/template
        Optional query params: category_id, is_featured, is_new_template,
        name_contains.
        """
        params: dict[str, Any] = {}
        if category_id is not None:
            params["category_id"] = category_id
        if is_featured is not None:
            params["is_featured"] = str(is_featured).lower()
        if is_new_template is not None:
            params["is_new_template"] = str(is_new_template).lower()
        if name_contains is not None:
            params["name_contains"] = name_contains
        data = self.request(
            "GET",
            "/api/template-center/template",
            params=params or None,
            require_auth=False,
        )
        return self._extract_list({"data": data} if not isinstance(data, dict) else data)

    def get_template(self, view_id: str) -> dict[str, Any]:
        """Get a single template by view_id.

        GET /api/template-center/template/{view_id}
        """
        data = self.request(
            "GET",
            f"/api/template-center/template/{view_id}",
            require_auth=False,
        )
        template = self._extract_data({"data": data} if not isinstance(data, dict) else data)
        if not isinstance(template, dict):
            raise AppFlowySchemaError("Expected AppFlowy template response", payload=data)
        return template

    def get_template_homepage(
        self,
        *,
        per_count: int | None = None,
    ) -> dict[str, Any]:
        """Get the AppFlowy template home page (featured/new/categories).

        GET /api/template-center/homepage
        Optional query param: per_count.
        """
        params: dict[str, Any] = {}
        if per_count is not None:
            params["per_count"] = per_count
        data = self.request(
            "GET",
            "/api/template-center/homepage",
            params=params or None,
            require_auth=False,
        )
        homepage = self._extract_data({"data": data} if not isinstance(data, dict) else data)
        if not isinstance(homepage, dict):
            raise AppFlowySchemaError("Expected AppFlowy template homepage response", payload=data)
        return homepage

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

    def _require_publish_writes_enabled(self) -> None:
        """Require both APPFLOWY_ALLOW_WRITES and APPFLOWY_ALLOW_PUBLISH_WRITES.

        Publishing is external-facing and irreversible in effect, so it needs
        an explicit second gate beyond the ordinary write guard.
        """
        self._require_writes_enabled()
        if not self.config.allow_publish_writes:
            raise AppFlowyError(
                "Publish writes are disabled. "
                "Set APPFLOWY_ALLOW_PUBLISH_WRITES=true "
                "(also requires APPFLOWY_ALLOW_WRITES=true) to enable page publish/unpublish."
            )

    @staticmethod
    def _infer_media_file_type(path: Path) -> str:
        suffix = path.suffix.lower().lstrip(".")
        if suffix in {"jpg", "jpeg", "png", "gif"}:
            return "Image"
        if suffix in {"zip", "rar", "tar"}:
            return "Archive"
        if suffix in {"mp4", "mov", "avi"}:
            return "Video"
        if suffix in {"mp3", "wav"}:
            return "Audio"
        if suffix == "txt":
            return "Text"
        if suffix in {"doc", "docx"}:
            return "Document"
        if suffix in {"html", "htm"}:
            return "Link"
        return "Other"

    @staticmethod
    def _extract_data(data: dict[str, Any]) -> Any:
        return data.get("data", data)

    @classmethod
    def _extract_list(cls, data: dict[str, Any]) -> list[dict[str, Any]]:
        payload = cls._extract_data(data)
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            for key in (
                "items",
                "rows",
                "databases",
                "workspaces",
                "members",
                "blobs",
                "views",
                "categories",
                "templates",
                "creators",
            ):
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


def _iter_database_view_items(collab: Any) -> list[tuple[str, dict[str, Any]]]:
    """Return database view items from all observed collab JSON shapes."""
    if not isinstance(collab, dict):
        return []

    def _views_to_items(views: Any) -> list[tuple[str, dict[str, Any]]]:
        if not isinstance(views, dict):
            return []
        out: list[tuple[str, dict[str, Any]]] = []
        for view_id, view_data in views.items():
            if isinstance(view_data, dict):
                out.append((str(view_id), view_data))
        return out

    nested_collab = collab.get("collab")
    if isinstance(nested_collab, dict):
        db = nested_collab.get("database")
        if isinstance(db, dict):
            results = _views_to_items(db.get("views"))
            if results:
                return results

    results = _views_to_items(collab.get("views"))
    if results:
        return results

    for key in ("database_inline_views", "inline_views"):
        results = _views_to_items(collab.get(key))
        if results:
            return results

    return []


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
    return [
        {"view_id": view_id, "row_orders": _coerce_row_orders(view_data.get("row_orders"))}
        for view_id, view_data in _iter_database_view_items(collab)
    ]


def _extract_view_configs(collab: Any) -> list[dict[str, Any]]:
    """Extract normalized database view configuration from collab JSON.

    The raw AppFlowy view object contains many fields. This helper keeps the
    configuration surface relevant to humans: layout, layout settings, filters,
    sorts, group settings, field settings, field order and row count.
    """
    out: list[dict[str, Any]] = []
    for view_id, view_data in _iter_database_view_items(collab):
        row_orders = _coerce_row_orders(view_data.get("row_orders"))
        field_orders = _coerce_field_orders(view_data.get("field_orders"))
        out.append(
            {
                "view_id": view_id,
                "name": view_data.get("name"),
                "database_id": view_data.get("database_id"),
                "layout": view_data.get("layout"),
                "layout_name": _layout_name(view_data.get("layout")),
                "is_inline": view_data.get("is_inline"),
                "layout_settings": _dict_or_empty(view_data.get("layout_settings")),
                "filters": _list_or_empty(view_data.get("filters")),
                "sorts": _list_or_empty(view_data.get("sorts")),
                "group_settings": _normalise_group_settings(view_data.get("group_settings")),
                "field_settings": _normalise_field_settings(view_data.get("field_settings")),
                "field_orders": field_orders,
                "field_order_count": len(field_orders),
                "row_order_count": len(row_orders),
                "created_at": view_data.get("created_at"),
                "modified_at": view_data.get("modified_at"),
            }
        )
    return out


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


def _coerce_field_orders(raw: Any) -> list[str]:
    """Normalise field_orders to a flat list of field-id strings."""
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            field_id = item.get("id") or item.get("field_id")
            if isinstance(field_id, str):
                out.append(field_id)
    return out


def _dict_or_empty(raw: Any) -> dict[str, Any]:
    return raw if isinstance(raw, dict) else {}


def _list_or_empty(raw: Any) -> list[Any]:
    return raw if isinstance(raw, list) else []


def _layout_name(raw: Any) -> str | None:
    layout_id: int | None = None
    if isinstance(raw, int):
        layout_id = raw
    elif isinstance(raw, str) and raw.isdigit():
        layout_id = int(raw)
    if layout_id is None:
        return None
    return {0: "Grid", 1: "Board", 2: "Calendar"}.get(layout_id)


def _normalise_field_settings(raw: Any) -> dict[str, dict[str, Any]]:
    """Return field settings keyed by field id with common knobs surfaced."""
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for field_id, settings in raw.items():
        if not isinstance(settings, dict):
            continue
        out[str(field_id)] = {
            "visibility": settings.get("visibility"),
            "width": settings.get("width"),
            "wrap_cell_content": settings.get("wrap_cell_content", settings.get("wrap")),
            "raw": settings,
        }
    return out


def _normalise_group_settings(raw: Any) -> list[dict[str, Any]]:
    """Return board/group settings with group ids and visibility surfaced."""
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for setting in raw:
        if not isinstance(setting, dict):
            continue
        groups = []
        raw_groups = setting.get("groups")
        if isinstance(raw_groups, list):
            for group in raw_groups:
                if isinstance(group, dict):
                    groups.append(
                        {
                            "id": group.get("id"),
                            "visible": group.get("visible"),
                            "raw": group,
                        }
                    )
                elif isinstance(group, str):
                    groups.append({"id": group, "visible": None, "raw": group})
        out.append(
            {
                "id": setting.get("id"),
                "field_id": setting.get("field_id"),
                "field_type": setting.get("ty", setting.get("field_type")),
                "content": setting.get("content"),
                "groups": groups,
                "raw": setting,
            }
        )
    return out
