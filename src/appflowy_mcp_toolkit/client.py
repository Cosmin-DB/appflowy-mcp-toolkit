from __future__ import annotations

from typing import Any

import httpx

from .client_parts.databases import DatabaseMixin
from .client_parts.diagnostics import DiagnosticMixin
from .client_parts.files import FileMixin
from .client_parts.pages import PageMixin
from .client_parts.publishing import PublishingMixin
from .client_parts.tasks_rows import TaskRowMixin
from .client_parts.templates import TemplateMixin
from .client_parts.workspaces import WorkspaceMixin
from .config import AppFlowyConfig
from .errors import AppFlowyError, AppFlowySchemaError, classify_http_error
from .rate_limit import RateLimiter


class AppFlowyClient(
    WorkspaceMixin,
    PublishingMixin,
    FileMixin,
    PageMixin,
    DatabaseMixin,
    TaskRowMixin,
    DiagnosticMixin,
    TemplateMixin,
):
    """Small REST client for AppFlowy Cloud/self-hosted API."""

    def __init__(
        self,
        config: AppFlowyConfig | None = None,
        *,
        http_client: httpx.Client | None = None,
        rate_limiter: RateLimiter | None = None,
    ):
        self.config = config or AppFlowyConfig.from_env()
        self._client = http_client or httpx.Client(timeout=self.config.timeout_seconds)
        self._owns_client = http_client is None
        self._rate_limiter = rate_limiter or RateLimiter.from_config(self.config)

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
        self._rate_limiter.check(method, path)
        headers = {"Accept": "application/json"}
        if require_auth:
            headers["Authorization"] = f"Bearer {self.config.require_token()}"
        try:
            response = self._client.request(method, url, headers=headers, params=params, json=json)
        finally:
            self._rate_limiter.release_concurrent()
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
        self._rate_limiter.check(method, path)
        headers = {"Accept": "application/octet-stream", "Content-Type": content_type}
        if require_auth:
            headers["Authorization"] = f"Bearer {self.config.require_token()}"
        try:
            response = self._client.request(method, url, headers=headers, content=content)
        finally:
            self._rate_limiter.release_concurrent()
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
        self._rate_limiter.check(method, path)
        headers = {"Accept": "application/json", "Content-Type": content_type}
        if require_auth:
            headers["Authorization"] = f"Bearer {self.config.require_token()}"
        try:
            response = self._client.request(method, url, headers=headers, content=content)
        finally:
            self._rate_limiter.release_concurrent()
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
        self._rate_limiter.check(method, path)
        headers = {"Accept": "application/octet-stream"}
        if require_auth:
            headers["Authorization"] = f"Bearer {self.config.require_token()}"
        try:
            response = self._client.request(method, url, headers=headers)
        finally:
            self._rate_limiter.release_concurrent()
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
            allow_publish_writes=self.config.allow_publish_writes,
            allow_local_file_reads=self.config.allow_local_file_reads,
            allowed_file_roots=self.config.allowed_file_roots,
            rate_limit_enabled=self.config.rate_limit_enabled,
            rate_limit_calls_per_minute=self.config.rate_limit_calls_per_minute,
            rate_limit_writes_per_minute=self.config.rate_limit_writes_per_minute,
            rate_limit_blob_collab_per_minute=self.config.rate_limit_blob_collab_per_minute,
            rate_limit_max_concurrent=self.config.rate_limit_max_concurrent,
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
