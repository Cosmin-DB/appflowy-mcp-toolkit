from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any
from urllib.parse import quote

from appflowy_mcp_toolkit.client_parts.base import ClientCore
from appflowy_mcp_toolkit.errors import AppFlowyError, AppFlowySchemaError


class FileMixin(ClientCore):
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
        """Validate and upload a local file to AppFlowy v1 blob storage.

        Security gates (all must pass for live execution):
          - APPFLOWY_ALLOW_WRITES=true
          - APPFLOWY_ALLOW_LOCAL_FILE_READS=true
          - file_path must resolve inside APPFLOWY_ALLOWED_FILE_ROOTS
            (prevents path traversal and symlink escape)

        Dry-run is safe: uses only stat() for file size, does NOT read
        file bytes and makes no network calls.
        """
        input_path = Path(file_path)
        guessed_type = (
            content_type or mimetypes.guess_type(input_path.name)[0] or "application/octet-stream"
        )
        encoded_parent_dir = quote(parent_dir, safe="")
        api_path = f"/api/file_storage/{workspace_id}/v1/blob/{encoded_parent_dir}"

        if dry_run:
            # Stat only — no file content read, no network call.
            # Still validate that the path passes the allowed-roots policy so
            # a dry-run surfaces safety errors early.
            resolved = self._require_local_file_read_allowed(input_path)
            try:
                file_size = resolved.stat().st_size
            except OSError:
                file_size = None
            return {
                "dry_run": True,
                "method": "PUT",
                "path": api_path,
                "file_path": str(resolved),
                "filename": resolved.name,
                "content_type": guessed_type,
                "content_length": file_size,
            }

        # Live path: full gate check then read and upload.
        resolved = self._require_local_file_read_allowed(input_path)
        content = resolved.read_bytes()
        return self.upload_file_blob_v1(
            workspace_id,
            parent_dir,
            content=content,
            content_type=guessed_type,
            dry_run=False,
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

    def _require_local_file_read_allowed(self, file_path: Path) -> Path:
        """Validate that file_path is safe to read for upload.

        Checks (in order):
        1. APPFLOWY_ALLOW_LOCAL_FILE_READS must be true.
        2. APPFLOWY_ALLOWED_FILE_ROOTS must be set and non-empty.
        3. The realpath of file_path must be inside one of the allowed roots
           (prevents traversal and symlink escape).

        Returns the resolved Path on success.  Raises AppFlowyError on any
        failure.
        """
        if not self.config.allow_local_file_reads:
            raise AppFlowyError(
                "Local file reads are disabled. "
                "Set APPFLOWY_ALLOW_LOCAL_FILE_READS=true to enable local file uploads."
            )
        if not self.config.allowed_file_roots:
            raise AppFlowyError(
                "No allowed file roots configured. "
                "Set APPFLOWY_ALLOWED_FILE_ROOTS to a colon-separated (Linux/macOS) or "
                "semicolon-separated (Windows) list of allowed directories "
                "before reading local files for upload."
            )
        try:
            resolved = file_path.resolve(strict=True)
        except (OSError, ValueError) as exc:
            raise AppFlowyError(f"Cannot resolve file path {str(file_path)!r}: {exc}") from exc
        allowed = [Path(r).resolve() for r in self.config.allowed_file_roots]
        for root in allowed:
            try:
                resolved.relative_to(root)
                return resolved
            except ValueError:
                continue
        raise AppFlowyError(
            f"File path {str(resolved)!r} is not inside any allowed root. "
            f"Allowed roots: {[str(r) for r in allowed]!r}. "
            "Update APPFLOWY_ALLOWED_FILE_ROOTS to include the required directory."
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
