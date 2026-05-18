from __future__ import annotations

from typing import Any

from appflowy_mcp_toolkit.client_parts.base import ClientCore
from appflowy_mcp_toolkit.errors import AppFlowySchemaError


class TemplateMixin(ClientCore):
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
