from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import httpx

from .config import AppFlowyConfig
from .errors import AppFlowyError, AppFlowySchemaError, classify_http_error


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

    def list_workspaces(
        self, *, include_member_count: bool = False, include_role: bool = False
    ) -> list[dict[str, Any]]:
        data = self.request(
            "GET",
            "/api/workspace",
            params={"include_member_count": include_member_count, "include_role": include_role},
        )
        return self._extract_list(data)

    def create_workspace(self, name: str, *, dry_run: bool = True) -> dict[str, Any]:
        payload = {"workspace_name": name}
        if dry_run:
            return {"dry_run": True, "method": "POST", "path": "/api/workspace", "json": payload}
        self._require_writes_enabled()
        return self.request("POST", "/api/workspace", json=payload)

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

    def list_databases(self, workspace_id: str) -> list[dict[str, Any]]:
        data = self.request("GET", f"/api/workspace/{workspace_id}/database")
        return self._extract_list(data)

    def list_database_fields(self, workspace_id: str, database_id: str) -> list[dict[str, Any]]:
        data = self.request("GET", f"/api/workspace/{workspace_id}/database/{database_id}/fields")
        return self._extract_list(data)

    def list_database_row_ids(self, workspace_id: str, database_id: str) -> list[dict[str, Any]]:
        data = self.request("GET", f"/api/workspace/{workspace_id}/database/{database_id}/row")
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
            for key in ("items", "rows", "databases", "workspaces"):
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
