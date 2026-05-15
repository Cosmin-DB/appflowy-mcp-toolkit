from __future__ import annotations

import httpx

from appflowy_mcp_toolkit.cli.main import main


def test_cli_health(monkeypatch, capsys):
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": []})

    from appflowy_mcp_toolkit import client as client_module

    original = client_module.httpx.Client

    def fake_client(*_args, **_kwargs):
        return original(transport=httpx.MockTransport(handler))

    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_ACCESS_TOKEN", "test-token")
    monkeypatch.setattr(client_module.httpx, "Client", fake_client)

    assert main(["health"]) == 0
    assert '"ok": true' in capsys.readouterr().out
