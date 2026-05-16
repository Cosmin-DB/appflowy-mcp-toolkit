from __future__ import annotations

import json

import httpx

from appflowy_mcp_toolkit.cli.main import main


def _patch_client(monkeypatch, handler):
    """Patch httpx.Client in the client module to use a mock transport."""
    from appflowy_mcp_toolkit import client as client_module

    original = client_module.httpx.Client

    def fake_client(*_args, **_kwargs):
        return original(transport=httpx.MockTransport(handler))

    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", "test-token")
    monkeypatch.setattr(client_module.httpx, "Client", fake_client)


def test_cli_health(monkeypatch, capsys):
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": []})

    _patch_client(monkeypatch, handler)

    assert main(["health"]) == 0
    assert '"ok": true' in capsys.readouterr().out


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
