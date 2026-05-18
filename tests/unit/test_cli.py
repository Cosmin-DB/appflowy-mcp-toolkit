from __future__ import annotations

import json

import httpx

from appflowy_mcp_toolkit.cli.main import main

# ---------------------------------------------------------------------------
# doctor tests
# ---------------------------------------------------------------------------


def test_doctor_offline_no_client(monkeypatch, capsys):
    """doctor without --network must not instantiate AppFlowyClient."""
    from unittest.mock import patch as _patch

    monkeypatch.delenv("APPFLOWY_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("APPFLOWY_BASE_URL", raising=False)

    collab_stub = {"ok": False, "checks": {}}

    with (
        _patch(
            "appflowy_mcp_toolkit.collab.collab_delete.check_collab_helper_setup",
            return_value=collab_stub,
        ),
        _patch(
            "appflowy_mcp_toolkit.cli.main.AppFlowyClient",
            side_effect=AssertionError("doctor must not create a client without --network"),
        ),
    ):
        rc = main(["doctor"])

    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert "version" in out
    assert "env" in out
    assert "collab_helper" in out
    assert "mcp" in out
    assert "network_check" not in out  # only present with --network


def test_doctor_masks_token_value(monkeypatch, capsys):
    """doctor must report only a boolean for APPFLOWY_ACCESS_TOKEN, never its value."""
    from unittest.mock import patch as _patch

    monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", "super-secret-token")
    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://my.selfhosted.example")

    with _patch(
        "appflowy_mcp_toolkit.collab.collab_delete.check_collab_helper_setup",
        return_value={"ok": True, "checks": {}},
    ):
        rc = main(["doctor"])

    assert rc == 0
    raw = capsys.readouterr().out
    # Token value must not appear anywhere in the output
    assert "super-secret-token" not in raw
    out = json.loads(raw)
    assert out["env"]["APPFLOWY_ACCESS_TOKEN_present"] is True
    assert out["env"]["APPFLOWY_BASE_URL"] == "https://my.selfhosted.example"


def test_doctor_token_absent_reports_false(monkeypatch, capsys):
    from unittest.mock import patch as _patch

    monkeypatch.delenv("APPFLOWY_ACCESS_TOKEN", raising=False)

    with _patch(
        "appflowy_mcp_toolkit.collab.collab_delete.check_collab_helper_setup",
        return_value={"ok": False, "checks": {}},
    ):
        rc = main(["doctor"])

    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["env"]["APPFLOWY_ACCESS_TOKEN_present"] is False


def test_doctor_with_network_calls_health_check(monkeypatch, capsys):
    """doctor --network must call health_check via AppFlowyClient."""
    from unittest.mock import MagicMock
    from unittest.mock import patch as _patch

    monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")

    health_result = {"ok": True, "code": 0}
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.health_check.return_value = health_result

    with (
        _patch(
            "appflowy_mcp_toolkit.collab.collab_delete.check_collab_helper_setup",
            return_value={"ok": True, "checks": {}},
        ),
        _patch(
            "appflowy_mcp_toolkit.cli.main.AppFlowyClient",
            return_value=mock_client,
        ),
    ):
        rc = main(["doctor", "--network"])

    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["network_check"] == health_result
    mock_client.health_check.assert_called_once()


def test_doctor_network_without_token_returns_error(monkeypatch, capsys):
    """doctor --network without a token must report an error, not crash."""
    from unittest.mock import patch as _patch

    monkeypatch.delenv("APPFLOWY_ACCESS_TOKEN", raising=False)

    with (
        _patch(
            "appflowy_mcp_toolkit.collab.collab_delete.check_collab_helper_setup",
            return_value={"ok": False, "checks": {}},
        ),
        _patch(
            "appflowy_mcp_toolkit.cli.main.AppFlowyClient",
            side_effect=AssertionError("must not create client when token absent"),
        ),
    ):
        rc = main(["doctor", "--network"])

    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["network_check"]["ok"] is False
    assert "APPFLOWY_ACCESS_TOKEN" in out["network_check"]["error"]


def test_doctor_next_steps_present(monkeypatch, capsys):
    """next_steps list must always be present and non-empty."""
    from unittest.mock import patch as _patch

    monkeypatch.delenv("APPFLOWY_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("APPFLOWY_BASE_URL", raising=False)

    with _patch(
        "appflowy_mcp_toolkit.collab.collab_delete.check_collab_helper_setup",
        return_value={"ok": False, "checks": {}},
    ):
        main(["doctor"])

    out = json.loads(capsys.readouterr().out)
    assert isinstance(out["next_steps"], list)
    assert len(out["next_steps"]) > 0


# ---------------------------------------------------------------------------
# setup-check tests (unchanged behaviour)
# ---------------------------------------------------------------------------


def _patch_client(monkeypatch, handler):
    """Patch httpx.Client in the client module to use a mock transport."""
    import httpx as _httpx
    from appflowy_mcp_toolkit import client as client_module

    _real_client = _httpx.Client  # always the real class, regardless of prior patches

    def fake_client(*_args, **_kwargs):
        return _real_client(transport=_httpx.MockTransport(handler))

    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", "test-token")
    monkeypatch.setattr(client_module.httpx, "Client", fake_client)


def test_cli_health(monkeypatch, capsys):
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": []})

    _patch_client(monkeypatch, handler)

    assert main(["health"]) == 0
    assert '"ok": true' in capsys.readouterr().out


def test_cli_setup_check_does_not_require_appflowy_config(monkeypatch, capsys):
    from unittest.mock import patch as _patch

    monkeypatch.delenv("APPFLOWY_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("APPFLOWY_BASE_URL", raising=False)

    setup_result = {
        "ok": False,
        "install_command": "cd src/appflowy_mcp_toolkit/collab && npm install",
        "checks": {"node": {"ok": False, "message": "Node.js was not found"}},
    }

    with (
        _patch(
            "appflowy_mcp_toolkit.collab.collab_delete.check_collab_helper_setup",
            return_value=setup_result,
        ) as mock_setup,
        _patch(
            "appflowy_mcp_toolkit.cli.main.AppFlowyClient",
            side_effect=AssertionError("setup-check must not create a client"),
        ),
    ):
        assert main(["setup-check"]) == 0

    parsed = json.loads(capsys.readouterr().out)
    assert parsed == setup_result
    mock_setup.assert_called_once_with()


def test_cli_collab_json(monkeypatch, capsys):
    fake_collab = {"views": {"view_001": {"row_orders": ["row_aaa"]}}}

    def handler(request: httpx.Request) -> httpx.Response:
        assert "/collab/" in request.url.path
        # integer 1 must be sent, not the string "Database"
        assert request.url.params["collab_type"] == "1"
        return httpx.Response(200, json={"data": fake_collab})

    _patch_client(monkeypatch, handler)

    assert main(["collab-json", "--workspace-id", "ws_001", "--object-id", "db_001"]) == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed == fake_collab


def test_cli_row_orders(monkeypatch, capsys):
    # Use the live-shape fixture (collab.database.views) to exercise the fixed extractor.
    fake_collab = {
        "collab": {
            "database": {
                "views": {
                    "view_001": {"row_orders": [{"id": "row_aaa"}, {"id": "row_bbb"}]},
                }
            }
        }
    }

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": fake_collab})

    _patch_client(monkeypatch, handler)

    assert main(["row-orders", "--workspace-id", "ws_001", "--database-id", "db_001"]) == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert len(parsed) == 1
    assert parsed[0]["view_id"] == "view_001"
    assert parsed[0]["row_orders"] == ["row_aaa", "row_bbb"]


def test_cli_navigation_lists(monkeypatch, capsys):
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(
            200, json={"data": [{"view_id": request.url.path.rsplit("/", 1)[-1]}]}
        )

    _patch_client(monkeypatch, handler)

    assert main(["recent", "--workspace-id", "ws_001"]) == 0
    assert json.loads(capsys.readouterr().out) == [{"view_id": "recent"}]
    assert main(["favorites", "--workspace-id", "ws_001"]) == 0
    assert json.loads(capsys.readouterr().out) == [{"view_id": "favorite"}]
    assert main(["trash", "--workspace-id", "ws_001"]) == 0
    assert json.loads(capsys.readouterr().out) == [{"view_id": "trash"}]
    assert seen == [
        "/api/workspace/ws_001/recent",
        "/api/workspace/ws_001/favorite",
        "/api/workspace/ws_001/trash",
    ]


def test_cli_page_view_commands_dry_run(monkeypatch, capsys):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/workspace/ws_001/page-view/view_001"
        return httpx.Response(200, json={"data": {"view": {"id": "view_001"}}})

    _patch_client(monkeypatch, handler)

    assert main(["page-view", "--workspace-id", "ws_001", "--view-id", "view_001"]) == 0
    assert json.loads(capsys.readouterr().out)["view"]["id"] == "view_001"

    assert (
        main(
            [
                "create-page",
                "--workspace-id",
                "ws_001",
                "--parent-view-id",
                "parent",
                "--layout",
                "0",
                "--name",
                "Page",
                "--page-data-json",
                "{}",
            ]
        )
        == 0
    )
    created = json.loads(capsys.readouterr().out)
    assert created["dry_run"] is True
    assert created["path"] == "/api/workspace/ws_001/page-view"
    assert created["json"]["parent_view_id"] == "parent"

    assert (
        main(
            [
                "move-page",
                "--workspace-id",
                "ws_001",
                "--view-id",
                "view_001",
                "--new-parent-view-id",
                "parent2",
            ]
        )
        == 0
    )
    moved = json.loads(capsys.readouterr().out)
    assert moved["path"] == "/api/workspace/ws_001/page-view/view_001/move"
    assert moved["json"] == {"new_parent_view_id": "parent2"}


def test_cli_space_and_folder_dry_run(capsys):
    assert (
        main(
            [
                "create-space",
                "--workspace-id",
                "ws_001",
                "--name",
                "Engineering",
                "--space-permission",
                "0",
            ]
        )
        == 0
    )
    created_space = json.loads(capsys.readouterr().out)
    assert created_space["path"] == "/api/workspace/ws_001/space"
    assert created_space["json"]["name"] == "Engineering"

    assert (
        main(
            [
                "create-folder",
                "--workspace-id",
                "ws_001",
                "--parent-view-id",
                "parent",
                "--name",
                "Folder",
            ]
        )
        == 0
    )
    created_folder = json.loads(capsys.readouterr().out)
    assert created_folder["path"] == "/api/workspace/ws_001/folder-view"
    assert created_folder["json"]["parent_view_id"] == "parent"


def test_cli_updated_rows(monkeypatch, capsys):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/workspace/ws_001/database/db_001/row/updated"
        assert request.url.params["after"] == "2026-05-16T10:00:00Z"
        return httpx.Response(200, json={"data": [{"row_id": "row_aaa"}]})

    _patch_client(monkeypatch, handler)

    assert (
        main(
            [
                "updated-rows",
                "--workspace-id",
                "ws_001",
                "--database-id",
                "db_001",
                "--after",
                "2026-05-16T10:00:00Z",
            ]
        )
        == 0
    )
    parsed = json.loads(capsys.readouterr().out)
    assert parsed == [{"row_id": "row_aaa"}]


def test_cli_quick_notes(monkeypatch, capsys):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/workspace/ws_001/quick-note"
        assert request.url.params["search_term"] == "pple"
        assert request.url.params["offset"] == "1"
        assert request.url.params["limit"] == "2"
        return httpx.Response(
            200,
            json={
                "data": {
                    "quick_notes": [{"id": "note_001", "data": []}],
                    "has_more": False,
                }
            },
        )

    _patch_client(monkeypatch, handler)

    assert (
        main(
            [
                "quick-notes",
                "--workspace-id",
                "ws_001",
                "--search-term",
                "pple",
                "--offset",
                "1",
                "--limit",
                "2",
            ]
        )
        == 0
    )
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["quick_notes"][0]["id"] == "note_001"
    assert parsed["has_more"] is False


def test_cli_quick_note_mutations_are_dry_run(monkeypatch, capsys):
    from unittest.mock import patch as _patch

    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", "test-token")

    with _patch(
        "appflowy_mcp_toolkit.client.AppFlowyClient.create_quick_note",
        return_value={"dry_run": True, "method": "POST"},
    ) as mock_create:
        rc = main(
            [
                "create-quick-note",
                "--workspace-id",
                "ws_001",
                "--data-json",
                '[{"type":"paragraph"}]',
            ]
        )
    assert rc == 0
    assert json.loads(capsys.readouterr().out)["dry_run"] is True
    mock_create.assert_called_once_with(
        "ws_001",
        data=[{"type": "paragraph"}],
        dry_run=True,
    )

    with _patch(
        "appflowy_mcp_toolkit.client.AppFlowyClient.update_quick_note",
        return_value={"dry_run": True, "method": "PUT"},
    ) as mock_update:
        rc = main(
            [
                "update-quick-note",
                "--workspace-id",
                "ws_001",
                "--quick-note-id",
                "note_001",
                "--data-json",
                '{"text":"updated"}',
            ]
        )
    assert rc == 0
    assert json.loads(capsys.readouterr().out)["dry_run"] is True
    mock_update.assert_called_once_with(
        "ws_001",
        "note_001",
        data={"text": "updated"},
        dry_run=True,
    )

    with _patch(
        "appflowy_mcp_toolkit.client.AppFlowyClient.delete_quick_note",
        return_value={"dry_run": True, "method": "DELETE"},
    ) as mock_delete:
        rc = main(
            [
                "delete-quick-note",
                "--workspace-id",
                "ws_001",
                "--quick-note-id",
                "note_001",
            ]
        )
    assert rc == 0
    assert json.loads(capsys.readouterr().out)["dry_run"] is True
    mock_delete.assert_called_once_with("ws_001", "note_001", dry_run=True)


def test_cli_search(monkeypatch, capsys):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/search/ws_001"
        assert request.url.params["query"] == "project plan"
        assert request.url.params["limit"] == "3"
        assert request.url.params["preview_size"] == "80"
        assert request.url.params["score"] == "0.3"
        return httpx.Response(200, json={"data": [{"object_id": "page_aaa"}]})

    _patch_client(monkeypatch, handler)

    assert (
        main(
            [
                "search",
                "--workspace-id",
                "ws_001",
                "--query",
                "project plan",
                "--limit",
                "3",
                "--preview-size",
                "80",
                "--score",
                "0.3",
            ]
        )
        == 0
    )
    parsed = json.loads(capsys.readouterr().out)
    assert parsed == [{"object_id": "page_aaa"}]


def test_cli_workspace_readonly_commands(monkeypatch, capsys):
    responses = {
        "/api/workspace/ws_001/settings": {"data": {"workspace_id": "ws_001", "name": "Demo"}},
        "/api/workspace/ws_001/member": {"data": [{"email": "demo@example.test"}]},
        "/api/workspace/ws_001/usage": {"data": {"storage_bytes": 2048}},
        "/api/file_storage/ws_001/usage": {"data": {"consumed_capacity": 4096}},
        "/api/file_storage/ws_001/blobs": {"data": [{"file_id": "file_a"}]},
        "/api/file_storage/ws_001/metadata/file_a": {
            "data": {"file_id": "file_a", "file_size": 123}
        },
        "/api/file_storage/ws_001/v1/metadata/parent_a/file_a": {
            "data": {"file_id": "file_a", "file_size": 123}
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=responses[request.url.path])

    _patch_client(monkeypatch, handler)

    assert main(["workspace-settings", "--workspace-id", "ws_001"]) == 0
    assert json.loads(capsys.readouterr().out) == {"workspace_id": "ws_001", "name": "Demo"}

    assert main(["workspace-members", "--workspace-id", "ws_001"]) == 0
    assert json.loads(capsys.readouterr().out) == [{"email": "demo@example.test"}]

    assert main(["workspace-usage", "--workspace-id", "ws_001"]) == 0
    assert json.loads(capsys.readouterr().out) == {"storage_bytes": 2048}

    assert main(["file-storage-usage", "--workspace-id", "ws_001"]) == 0
    assert json.loads(capsys.readouterr().out) == {"consumed_capacity": 4096}

    assert main(["file-storage-blobs", "--workspace-id", "ws_001"]) == 0
    assert json.loads(capsys.readouterr().out) == [{"file_id": "file_a"}]

    assert main(["file-metadata", "--workspace-id", "ws_001", "--file-id", "file_a"]) == 0
    assert json.loads(capsys.readouterr().out) == {"file_id": "file_a", "file_size": 123}

    assert (
        main(
            [
                "file-metadata-v1",
                "--workspace-id",
                "ws_001",
                "--parent-dir",
                "parent_a",
                "--file-id",
                "file_a",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out) == {"file_id": "file_a", "file_size": 123}


def test_cli_file_storage_write_commands(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("APPFLOWY_ALLOW_WRITES", "true")
    source = tmp_path / "spec.txt"
    source.write_text("hello media", encoding="utf-8")
    output = tmp_path / "downloaded.txt"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "PUT":
            assert request.url.path == "/api/file_storage/ws_001/v1/blob/db_001"
            assert request.content == b"hello media"
            return httpx.Response(200, json={"data": {"file_id": "file_a"}})
        if request.method == "GET":
            assert request.url.path == "/api/file_storage/ws_001/v1/blob/db_001/file_a"
            return httpx.Response(
                200, headers={"content-type": "text/plain"}, content=b"hello media"
            )
        if request.method == "DELETE":
            assert request.url.path == "/api/file_storage/ws_001/v1/blob/db_001/file_a"
            return httpx.Response(200, json={"data": {}})
        raise AssertionError(request)

    _patch_client(monkeypatch, handler)

    assert (
        main(
            [
                "upload-file-v1",
                "--workspace-id",
                "ws_001",
                "--parent-dir",
                "db_001",
                "--file-path",
                str(source),
                "--execute",
            ]
        )
        == 0
    )
    uploaded = json.loads(capsys.readouterr().out)
    assert uploaded["file_id"] == "file_a"

    assert (
        main(
            [
                "download-file-v1",
                "--workspace-id",
                "ws_001",
                "--parent-dir",
                "db_001",
                "--file-id",
                "file_a",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    downloaded = json.loads(capsys.readouterr().out)
    assert downloaded["content_length"] == len("hello media")
    assert output.read_text(encoding="utf-8") == "hello media"

    assert (
        main(
            [
                "delete-file-v1",
                "--workspace-id",
                "ws_001",
                "--parent-dir",
                "db_001",
                "--file-id",
                "file_a",
                "--execute",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["deleted"] is True


def test_cli_upload_media_file_returns_media_object(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("APPFLOWY_ALLOW_WRITES", "true")
    source = tmp_path / "spec.txt"
    source.write_text("hello media", encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PUT"
        return httpx.Response(200, json={"data": {"file_id": "file_a"}})

    _patch_client(monkeypatch, handler)

    assert (
        main(
            [
                "upload-media-file",
                "--workspace-id",
                "ws_001",
                "--database-id",
                "db_001",
                "--file-path",
                str(source),
                "--name",
                "Spec",
                "--execute",
            ]
        )
        == 0
    )
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["media"]["upload_type"] == "Cloud"
    assert parsed["media"]["url"].endswith("/api/file_storage/ws_001/v1/blob/db_001/file_a")


def test_cli_blob_diff(monkeypatch, capsys):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/workspace/ws_001/database/db_001/blob/diff"
        assert request.content == b"\x10\x01"
        return httpx.Response(200, content=b"\x30\x00")

    _patch_client(monkeypatch, handler)

    assert main(["blob-diff", "--workspace-id", "ws_001", "--database-id", "db_001"]) == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["status"] == 0
    assert parsed["counts"]["rows"] == 0


def test_cli_verify_row(monkeypatch, capsys):
    from unittest.mock import patch as _patch

    verify_result = {
        "row_id": "row-abc",
        "verified": True,
        "rest_row_list_present": True,
    }

    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", "test-token")

    with _patch(
        "appflowy_mcp_toolkit.client.AppFlowyClient.verify_database_row",
        return_value=verify_result,
    ) as mock_method:
        rc = main(
            [
                "verify-row",
                "--workspace-id",
                "ws_001",
                "--database-id",
                "db_001",
                "--row-id",
                "row-abc",
                "--skip-blob-diff",
            ]
        )

    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["verified"] is True
    mock_method.assert_called_once_with(
        "ws_001",
        "db_001",
        "row-abc",
        include_blob_diff=False,
    )


def test_cli_create_verified_row_dry_run(monkeypatch, capsys):
    from unittest.mock import patch as _patch

    dry_run_result = {
        "dry_run": True,
        "verification": {"would_check": ["REST row list"]},
    }

    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", "test-token")

    with _patch(
        "appflowy_mcp_toolkit.client.AppFlowyClient.create_database_row_verified",
        return_value=dry_run_result,
    ) as mock_method:
        rc = main(
            [
                "create-verified-row",
                "--workspace-id",
                "ws_001",
                "--database-id",
                "db_001",
                "--cells-json",
                '{"Description":"Test"}',
            ]
        )

    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["dry_run"] is True
    mock_method.assert_called_once_with(
        "ws_001",
        "db_001",
        cells={"Description": "Test"},
        document=None,
        dry_run=True,
        include_blob_diff=True,
    )


def test_cli_create_typed_row_dry_run(monkeypatch, capsys):
    from unittest.mock import patch as _patch

    dry_run_result = {
        "typed_cells": {"Description": "Test"},
        "result": {"dry_run": True},
    }

    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", "test-token")

    with _patch(
        "appflowy_mcp_toolkit.client.AppFlowyClient.create_typed_database_row_verified",
        return_value=dry_run_result,
    ) as mock_method:
        rc = main(
            [
                "create-typed-row",
                "--workspace-id",
                "ws_001",
                "--database-id",
                "db_001",
                "--values-json",
                '{"Description":"Test"}',
                "--skip-blob-diff",
            ]
        )

    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["typed_cells"]["Description"] == "Test"
    mock_method.assert_called_once_with(
        "ws_001",
        "db_001",
        values={"Description": "Test"},
        document=None,
        dry_run=True,
        include_blob_diff=False,
    )


def test_cli_upsert_typed_row_dry_run(monkeypatch, capsys):
    from unittest.mock import patch as _patch

    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", "test-token")

    with _patch(
        "appflowy_mcp_toolkit.client.AppFlowyClient.upsert_typed_database_row",
        return_value={"typed_cells": {"Description": "Test"}},
    ) as mock_method:
        rc = main(
            [
                "upsert-typed-row",
                "--workspace-id",
                "ws_001",
                "--database-id",
                "db_001",
                "--pre-hash",
                "task-1",
                "--values-json",
                '{"Description":"Test"}',
            ]
        )

    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["typed_cells"]["Description"] == "Test"
    mock_method.assert_called_once_with(
        "ws_001",
        "db_001",
        pre_hash="task-1",
        values={"Description": "Test"},
        document=None,
        dry_run=True,
    )


def test_cli_managed_task_verified_dry_run(monkeypatch, capsys):
    from unittest.mock import patch as _patch

    dry_run_result = {
        "dry_run": True,
        "verification": {"would_check": ["REST row list"]},
    }

    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", "test-token")

    with _patch(
        "appflowy_mcp_toolkit.client.AppFlowyClient.upsert_managed_task_verified",
        return_value=dry_run_result,
    ) as mock_method:
        rc = main(
            [
                "managed-task-verified",
                "--workspace-id",
                "ws_001",
                "--database-id",
                "db_001",
                "--task-key",
                "task-1",
                "--description",
                "Test",
                "--skip-blob-diff",
            ]
        )

    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["dry_run"] is True
    mock_method.assert_called_once_with(
        "ws_001",
        "db_001",
        task_key="task-1",
        description="Test",
        status=None,
        document=None,
        dry_run=True,
        include_blob_diff=False,
    )


def test_cli_task_commands_delegate_to_task_methods(monkeypatch, capsys):
    from unittest.mock import patch as _patch

    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", "test-token")

    with _patch(
        "appflowy_mcp_toolkit.client.AppFlowyClient.create_task",
        return_value={"dry_run": True},
    ) as mock_create:
        rc = main(
            [
                "create-task",
                "--workspace-id",
                "ws_001",
                "--database-id",
                "db_001",
                "--task-key",
                "task-1",
                "--description",
                "Test",
                "--skip-blob-diff",
            ]
        )
    assert rc == 0
    assert json.loads(capsys.readouterr().out)["dry_run"] is True
    mock_create.assert_called_once_with(
        "ws_001",
        "db_001",
        task_key="task-1",
        description="Test",
        status="To Do",
        document=None,
        dry_run=True,
        include_blob_diff=False,
    )

    with _patch(
        "appflowy_mcp_toolkit.client.AppFlowyClient.move_task",
        return_value={"dry_run": True},
    ) as mock_move:
        rc = main(
            [
                "move-task",
                "--workspace-id",
                "ws_001",
                "--database-id",
                "db_001",
                "--task-key",
                "task-1",
                "--status",
                "Doing",
            ]
        )
    assert rc == 0
    assert json.loads(capsys.readouterr().out)["dry_run"] is True
    mock_move.assert_called_once_with(
        "ws_001",
        "db_001",
        task_key="task-1",
        status="Doing",
        dry_run=True,
    )

    with _patch(
        "appflowy_mcp_toolkit.client.AppFlowyClient.move_task_by_row_id",
        return_value={"dry_run": True},
    ) as mock_move_by_id:
        rc = main(
            [
                "move-task-by-id",
                "--workspace-id",
                "ws_001",
                "--database-id",
                "db_001",
                "--row-id",
                "row-1",
                "--status",
                "Done",
            ]
        )
    assert rc == 0
    assert json.loads(capsys.readouterr().out)["dry_run"] is True
    mock_move_by_id.assert_called_once_with(
        "ws_001",
        "db_001",
        "row-1",
        status="Done",
        dry_run=True,
    )


def test_cli_update_row_by_id_dry_run(monkeypatch, capsys):
    from unittest.mock import patch as _patch

    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", "test-token")

    with _patch(
        "appflowy_mcp_toolkit.client.AppFlowyClient.update_database_row_by_id_collab",
        return_value={"dry_run": True, "row_id": "row-1"},
    ) as mock_method:
        rc = main(
            [
                "update-row-by-id",
                "--workspace-id",
                "ws_001",
                "--database-id",
                "db_001",
                "--row-id",
                "row-1",
                "--values-json",
                '{"Status":"Done"}',
            ]
        )

    assert rc == 0
    assert json.loads(capsys.readouterr().out)["row_id"] == "row-1"
    mock_method.assert_called_once_with(
        "ws_001",
        "db_001",
        "row-1",
        values={"Status": "Done"},
        dry_run=True,
    )


def test_cli_delete_row_dry_run(monkeypatch, capsys):
    """delete-row dry-run: patches the client method directly, no real subprocess."""
    from unittest.mock import patch as _patch

    dry_run_result = {
        "dry_run": True,
        "row_found": True,
        "views_affected": ["view-001"],
        "view_row_counts": {"view-001": {"before": 5, "after": 4}},
        "delta_update_bytes": 42,
    }

    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", "test-token")

    with _patch(
        "appflowy_mcp_toolkit.client.AppFlowyClient.delete_database_row_collab",
        return_value=dry_run_result,
    ) as mock_method:
        rc = main(
            [
                "delete-row",
                "--workspace-id",
                "ws_001",
                "--database-id",
                "db_001",
                "--row-id",
                "row-abc",
            ]
        )

    assert rc == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["dry_run"] is True
    assert parsed["row_found"] is True
    mock_method.assert_called_once_with("ws_001", "db_001", "row-abc", dry_run=True)
