from __future__ import annotations

from typing import Any

from appflowy_mcp_toolkit.client_parts.base import ClientCore
from appflowy_mcp_toolkit.errors import AppFlowySchemaError


class PublishingMixin(ClientCore):
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
