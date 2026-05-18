from __future__ import annotations

from typing import Any

from appflowy_mcp_toolkit.client_parts.base import ClientCore
from appflowy_mcp_toolkit.errors import AppFlowySchemaError


class PageMixin(ClientCore):
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
        from appflowy_mcp_toolkit.markdown import markdown_to_blocks

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
