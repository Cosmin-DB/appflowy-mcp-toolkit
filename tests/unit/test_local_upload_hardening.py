"""Tests for hardened local file upload paths.

Covers:
- dry-run: no read_bytes call, uses stat only
- dry-run: rejects path outside allowed roots (early validation)
- live: rejects without APPFLOWY_ALLOW_LOCAL_FILE_READS
- live: rejects without APPFLOWY_ALLOWED_FILE_ROOTS
- live: rejects path outside allowed roots
- live: rejects symlink that escapes allowed root
- live: accepts file inside allowed root and delegates to upload_file_blob_v1
- upload_file_as_media dry-run works via delegation
- CLI upload-file-v1 dry-run returns expected shape
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from appflowy_mcp_toolkit.config import AppFlowyConfig
from appflowy_mcp_toolkit.errors import AppFlowyError

# ---------------------------------------------------------------------------
# Helper: build a client with given config fields without env-var side effects
# ---------------------------------------------------------------------------


def _client(
    *,
    allow_writes: bool = False,
    allow_local_file_reads: bool = False,
    allowed_file_roots: tuple[str, ...] = (),
    allow_publish_writes: bool = False,
):
    from appflowy_mcp_toolkit.client import AppFlowyClient

    cfg = AppFlowyConfig(
        base_url="https://example.test",
        access_token="test-token",
        allow_writes=allow_writes,
        allow_local_file_reads=allow_local_file_reads,
        allowed_file_roots=allowed_file_roots,
        allow_publish_writes=allow_publish_writes,
    )
    return AppFlowyClient(cfg)


# ---------------------------------------------------------------------------
# Config: env parsing
# ---------------------------------------------------------------------------


def test_config_allow_local_file_reads_default(monkeypatch):
    monkeypatch.delenv("APPFLOWY_ALLOW_LOCAL_FILE_READS", raising=False)
    monkeypatch.delenv("APPFLOWY_ALLOWED_FILE_ROOTS", raising=False)
    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    cfg = AppFlowyConfig.from_env()
    assert cfg.allow_local_file_reads is False
    assert cfg.allowed_file_roots == ()


def test_config_allow_local_file_reads_true(monkeypatch, tmp_path):
    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_ALLOW_LOCAL_FILE_READS", "true")
    monkeypatch.setenv("APPFLOWY_ALLOWED_FILE_ROOTS", str(tmp_path))
    cfg = AppFlowyConfig.from_env()
    assert cfg.allow_local_file_reads is True
    assert str(tmp_path) in cfg.allowed_file_roots


def test_config_multiple_roots(monkeypatch, tmp_path):
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    root_a.mkdir()
    root_b.mkdir()
    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_ALLOW_LOCAL_FILE_READS", "true")
    monkeypatch.setenv(
        "APPFLOWY_ALLOWED_FILE_ROOTS",
        os.pathsep.join([str(root_a), str(root_b)]),
    )
    cfg = AppFlowyConfig.from_env()
    assert len(cfg.allowed_file_roots) == 2


# ---------------------------------------------------------------------------
# Dry-run: no read_bytes, uses stat, validates roots
# ---------------------------------------------------------------------------


def test_dry_run_does_not_call_read_bytes(tmp_path):
    allowed = tmp_path / "uploads"
    allowed.mkdir()
    test_file = allowed / "spec.txt"
    test_file.write_text("hello", encoding="utf-8")

    with (
        _client(
            allow_local_file_reads=True,
            allowed_file_roots=(str(allowed),),
        ) as client,
        patch.object(Path, "read_bytes") as mock_rb,
    ):
        result = client.upload_local_file_blob_v1("ws-1", "parent-dir", test_file, dry_run=True)
        mock_rb.assert_not_called()

    assert result["dry_run"] is True
    assert result["content_length"] == 5  # len("hello")
    assert "file_path" in result
    assert result["filename"] == "spec.txt"


def test_dry_run_rejects_path_outside_allowed_root(tmp_path):
    allowed = tmp_path / "uploads"
    allowed.mkdir()
    other = tmp_path / "secrets"
    other.mkdir()
    secret_file = other / "password.txt"
    secret_file.write_text("secret", encoding="utf-8")

    with (
        _client(
            allow_local_file_reads=True,
            allowed_file_roots=(str(allowed),),
        ) as client,
        pytest.raises(AppFlowyError, match="not inside any allowed root"),
    ):
        client.upload_local_file_blob_v1("ws-1", "parent-dir", secret_file, dry_run=True)


def test_dry_run_rejects_when_local_reads_disabled(tmp_path):
    allowed = tmp_path / "uploads"
    allowed.mkdir()
    test_file = allowed / "spec.txt"
    test_file.write_text("hello", encoding="utf-8")

    with (
        _client(
            allow_local_file_reads=False,
            allowed_file_roots=(str(allowed),),
        ) as client,
        pytest.raises(AppFlowyError, match="APPFLOWY_ALLOW_LOCAL_FILE_READS"),
    ):
        client.upload_local_file_blob_v1("ws-1", "parent-dir", test_file, dry_run=True)


def test_dry_run_rejects_when_no_roots_configured(tmp_path):
    test_file = tmp_path / "spec.txt"
    test_file.write_text("hello", encoding="utf-8")

    with (
        _client(allow_local_file_reads=True, allowed_file_roots=()) as client,
        pytest.raises(AppFlowyError, match="APPFLOWY_ALLOWED_FILE_ROOTS"),
    ):
        client.upload_local_file_blob_v1("ws-1", "parent-dir", test_file, dry_run=True)


# ---------------------------------------------------------------------------
# Live: gate enforcement
# ---------------------------------------------------------------------------


def test_live_rejects_without_allow_local_file_reads(tmp_path):
    allowed = tmp_path / "uploads"
    allowed.mkdir()
    test_file = allowed / "spec.txt"
    test_file.write_text("hello", encoding="utf-8")

    with (
        _client(
            allow_writes=True,
            allow_local_file_reads=False,
            allowed_file_roots=(str(allowed),),
        ) as client,
        pytest.raises(AppFlowyError, match="APPFLOWY_ALLOW_LOCAL_FILE_READS"),
    ):
        client.upload_local_file_blob_v1("ws-1", "parent-dir", test_file, dry_run=False)


def test_live_rejects_without_allowed_roots(tmp_path):
    test_file = tmp_path / "spec.txt"
    test_file.write_text("hello", encoding="utf-8")

    with (
        _client(
            allow_writes=True,
            allow_local_file_reads=True,
            allowed_file_roots=(),
        ) as client,
        pytest.raises(AppFlowyError, match="APPFLOWY_ALLOWED_FILE_ROOTS"),
    ):
        client.upload_local_file_blob_v1("ws-1", "parent-dir", test_file, dry_run=False)


def test_live_rejects_path_outside_allowed_root(tmp_path):
    allowed = tmp_path / "uploads"
    allowed.mkdir()
    other = tmp_path / "secrets"
    other.mkdir()
    secret_file = other / "password.txt"
    secret_file.write_text("secret", encoding="utf-8")

    with (
        _client(
            allow_writes=True,
            allow_local_file_reads=True,
            allowed_file_roots=(str(allowed),),
        ) as client,
        pytest.raises(AppFlowyError, match="not inside any allowed root"),
    ):
        client.upload_local_file_blob_v1("ws-1", "parent-dir", secret_file, dry_run=False)


def test_live_rejects_traversal_escape(tmp_path):
    """A path like allowed/../secrets must be rejected."""
    allowed = tmp_path / "uploads"
    allowed.mkdir()
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    secret_file = secrets / "private.key"
    secret_file.write_text("KEY", encoding="utf-8")

    # Construct a traversal path that starts inside allowed but escapes
    traversal_path = allowed / ".." / "secrets" / "private.key"

    with (
        _client(
            allow_writes=True,
            allow_local_file_reads=True,
            allowed_file_roots=(str(allowed),),
        ) as client,
        pytest.raises(AppFlowyError, match="not inside any allowed root"),
    ):
        client.upload_local_file_blob_v1("ws-1", "parent-dir", traversal_path, dry_run=False)


@pytest.mark.skipif(
    not hasattr(os, "symlink"),
    reason="symlinks not available on this platform",
)
def test_live_rejects_symlink_escape(tmp_path):
    """A symlink inside the allowed root pointing outside must be rejected."""
    allowed = tmp_path / "uploads"
    allowed.mkdir()
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    secret_file = secrets / "private.key"
    secret_file.write_text("KEY", encoding="utf-8")

    link = allowed / "evil_link.key"
    link.symlink_to(secret_file)

    with (
        _client(
            allow_writes=True,
            allow_local_file_reads=True,
            allowed_file_roots=(str(allowed),),
        ) as client,
        pytest.raises(AppFlowyError, match="not inside any allowed root"),
    ):
        client.upload_local_file_blob_v1("ws-1", "parent-dir", link, dry_run=False)


def test_live_accepted_inside_allowed_root_calls_upload(tmp_path):
    """File inside allowed root → reads bytes and calls upload_file_blob_v1."""
    allowed = tmp_path / "uploads"
    allowed.mkdir()
    test_file = allowed / "spec.txt"
    test_file.write_bytes(b"hello upload")

    mock_result = {"file_id": "fid-1", "url": "https://example.test/blob/fid-1"}

    with _client(  # noqa: SIM117
        allow_writes=True,
        allow_local_file_reads=True,
        allowed_file_roots=(str(allowed),),
    ) as client:
        with patch.object(client, "upload_file_blob_v1", return_value=mock_result) as mock_upload:
            result = client.upload_local_file_blob_v1("ws-1", "db-1", test_file, dry_run=False)

    mock_upload.assert_called_once()
    call_kwargs = mock_upload.call_args
    assert call_kwargs.kwargs["content"] == b"hello upload"
    assert call_kwargs.kwargs["dry_run"] is False
    assert result == mock_result


# ---------------------------------------------------------------------------
# upload_file_as_media: dry-run delegates properly
# ---------------------------------------------------------------------------


def test_upload_file_as_media_dry_run_shape(tmp_path):
    allowed = tmp_path / "media"
    allowed.mkdir()
    img = allowed / "photo.png"
    img.write_bytes(b"\x89PNG")  # 4 bytes fake PNG header

    with _client(
        allow_local_file_reads=True,
        allowed_file_roots=(str(allowed),),
    ) as client:
        result = client.upload_file_as_media("ws-1", "db-1", img, dry_run=True)

    assert result["upload"]["dry_run"] is True
    assert result["media"]["name"] == "photo.png"
    assert result["media"]["file_type"] == "Image"


def test_upload_file_as_media_propagates_local_read_error(tmp_path):
    """upload_file_as_media must propagate the local-read gate error."""
    test_file = tmp_path / "spec.txt"
    test_file.write_text("hello", encoding="utf-8")

    with (
        _client(allow_local_file_reads=False, allowed_file_roots=()) as client,
        pytest.raises(AppFlowyError, match="APPFLOWY_ALLOW_LOCAL_FILE_READS"),
    ):
        client.upload_file_as_media("ws-1", "db-1", test_file, dry_run=True)


# ---------------------------------------------------------------------------
# CLI dry-run: upload-file-v1
# ---------------------------------------------------------------------------


def test_cli_upload_file_v1_dry_run(monkeypatch, capsys, tmp_path):
    import json

    from appflowy_mcp_toolkit.cli.main import main

    allowed = tmp_path / "uploads"
    allowed.mkdir()
    test_file = allowed / "spec.txt"
    test_file.write_text("hello", encoding="utf-8")

    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("APPFLOWY_ALLOW_LOCAL_FILE_READS", "true")
    monkeypatch.setenv("APPFLOWY_ALLOWED_FILE_ROOTS", str(allowed))

    rc = main(
        [
            "upload-file-v1",
            "--workspace-id",
            "ws-1",
            "--parent-dir",
            "db-1",
            "--file-path",
            str(test_file),
        ]
    )
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["dry_run"] is True
    assert out["content_length"] == 5
    assert "file_path" in out


def test_cli_upload_file_v1_dry_run_rejects_unallowed_path(monkeypatch, capsys, tmp_path):
    from appflowy_mcp_toolkit.cli.main import main

    allowed = tmp_path / "uploads"
    allowed.mkdir()
    secret_dir = tmp_path / "secrets"
    secret_dir.mkdir()
    secret_file = secret_dir / "private.key"
    secret_file.write_text("KEY", encoding="utf-8")

    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("APPFLOWY_ALLOW_LOCAL_FILE_READS", "true")
    monkeypatch.setenv("APPFLOWY_ALLOWED_FILE_ROOTS", str(allowed))

    # Should raise SystemExit (non-zero) or AppFlowyError propagated as exit
    with pytest.raises((SystemExit, Exception)):
        main(
            [
                "upload-file-v1",
                "--workspace-id",
                "ws-1",
                "--parent-dir",
                "db-1",
                "--file-path",
                str(secret_file),
            ]
        )
