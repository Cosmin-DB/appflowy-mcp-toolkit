"""Tests for the in-process rate limiter."""

from __future__ import annotations

import httpx
import pytest

from appflowy_mcp_toolkit.config import AppFlowyConfig
from appflowy_mcp_toolkit.errors import AppFlowyError
from appflowy_mcp_toolkit.mcp import server as mcp_server
from appflowy_mcp_toolkit.rate_limit import RateLimiter, _is_blob_collab, _is_write

# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------


def test_write_methods_classified():
    assert _is_write("POST") is True
    assert _is_write("PUT") is True
    assert _is_write("PATCH") is True
    assert _is_write("DELETE") is True
    assert _is_write("GET") is False
    assert _is_write("get") is False  # case-insensitive


def test_blob_collab_paths_classified():
    assert _is_blob_collab("/api/file_storage/ws/v1/blob/db") is True
    assert _is_blob_collab("/api/workspace/v1/ws/collab/obj/json") is True
    assert _is_blob_collab("/api/workspace/ws/published-duplicate") is True
    assert _is_blob_collab("/api/workspace/ws/page-view/v/append-block") is True
    assert _is_blob_collab("/api/workspace/ws/collab/obj/web-update") is True
    assert _is_blob_collab("/api/workspace/ws/database/db/row") is False


# ---------------------------------------------------------------------------
# RateLimiter: bucket enforcement
# ---------------------------------------------------------------------------


def test_read_over_overall_limit_raises():
    limiter = RateLimiter(calls_per_minute=3)
    limiter.check("GET", "/api/workspace")
    limiter.check("GET", "/api/workspace")
    limiter.check("GET", "/api/workspace")
    with pytest.raises(AppFlowyError, match="Rate limit exceeded"):
        limiter.check("GET", "/api/workspace")


def test_write_over_write_limit_raises():
    limiter = RateLimiter(writes_per_minute=2)
    limiter.check("POST", "/api/workspace/ws/row")
    limiter.release_concurrent()
    limiter.check("PUT", "/api/workspace/ws/row")
    limiter.release_concurrent()
    with pytest.raises(AppFlowyError, match="write calls per minute"):
        limiter.check("DELETE", "/api/workspace/ws/row")


def test_read_does_not_consume_write_bucket():
    limiter = RateLimiter(writes_per_minute=1)
    # Many reads should not trigger write limit
    for _ in range(10):
        limiter.check("GET", "/api/workspace")
        limiter.release_concurrent()
    # One write should succeed
    limiter.check("POST", "/api/workspace/ws/row")
    limiter.release_concurrent()


def test_blob_collab_over_limit_raises():
    limiter = RateLimiter(blob_collab_per_minute=2)
    limiter.check("GET", "/api/workspace/v1/ws/collab/obj/json")
    limiter.release_concurrent()
    limiter.check("GET", "/api/workspace/v1/ws/collab/obj/json")
    limiter.release_concurrent()
    with pytest.raises(AppFlowyError, match="blob/collab calls per minute"):
        limiter.check("GET", "/api/workspace/v1/ws/collab/obj/json")


def test_concurrent_over_limit_raises():
    limiter = RateLimiter(max_concurrent=2)
    limiter.check("GET", "/api/workspace")
    limiter.check("GET", "/api/workspace")
    with pytest.raises(AppFlowyError, match="concurrent calls"):
        limiter.check("GET", "/api/workspace")
    # After release, another call should succeed
    limiter.release_concurrent()
    limiter.check("GET", "/api/workspace")  # should not raise


def test_disabled_limiter_never_raises():
    limiter = RateLimiter.disabled()
    for _ in range(1000):
        limiter.check("POST", "/api/workspace/v1/ws/collab/obj/web-update")
        limiter.release_concurrent()


# ---------------------------------------------------------------------------
# No global state leakage
# ---------------------------------------------------------------------------


def test_two_limiters_are_independent():
    a = RateLimiter(calls_per_minute=2)
    b = RateLimiter(calls_per_minute=2)
    a.check("GET", "/api/workspace")
    a.check("GET", "/api/workspace")
    # a is exhausted; b should still work
    b.check("GET", "/api/workspace")
    b.check("GET", "/api/workspace")
    with pytest.raises(AppFlowyError):
        a.check("GET", "/api/workspace")
    # b is also exhausted now
    with pytest.raises(AppFlowyError):
        b.check("GET", "/api/workspace")


def test_mcp_server_rate_limiter_is_shared_per_process():
    cfg = AppFlowyConfig(
        base_url="https://example.test",
        access_token="tok",
        rate_limit_enabled=True,
        rate_limit_calls_per_minute=2,
        rate_limit_writes_per_minute=0,
        rate_limit_blob_collab_per_minute=0,
        rate_limit_max_concurrent=0,
    )
    key = (
        cfg.rate_limit_enabled,
        cfg.rate_limit_calls_per_minute,
        cfg.rate_limit_writes_per_minute,
        cfg.rate_limit_blob_collab_per_minute,
        cfg.rate_limit_max_concurrent,
    )
    mcp_server._server_rate_limiters.pop(key, None)

    try:
        first = mcp_server._server_rate_limiter(cfg)
        second = mcp_server._server_rate_limiter(cfg)

        assert first is second
        first.check("GET", "/api/workspace")
        second.check("GET", "/api/workspace")
        with pytest.raises(AppFlowyError, match="overall calls per minute"):
            second.check("GET", "/api/workspace")
    finally:
        mcp_server._server_rate_limiters.pop(key, None)


# ---------------------------------------------------------------------------
# Config: env parsing
# ---------------------------------------------------------------------------


def test_config_rate_limit_defaults(monkeypatch):
    monkeypatch.delenv("APPFLOWY_RATE_LIMIT_ENABLED", raising=False)
    monkeypatch.delenv("APPFLOWY_RATE_LIMIT_CALLS_PER_MINUTE", raising=False)
    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    cfg = AppFlowyConfig.from_env()
    assert cfg.rate_limit_enabled is True
    assert cfg.rate_limit_calls_per_minute == 120
    assert cfg.rate_limit_writes_per_minute == 30
    assert cfg.rate_limit_blob_collab_per_minute == 20
    assert cfg.rate_limit_max_concurrent == 8


def test_config_rate_limit_disabled(monkeypatch):
    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_RATE_LIMIT_ENABLED", "false")
    cfg = AppFlowyConfig.from_env()
    assert cfg.rate_limit_enabled is False
    limiter = RateLimiter.from_config(cfg)
    # Disabled limiter should not raise regardless of call count
    for _ in range(200):
        limiter.check("POST", "/api/workspace/v1/ws/collab/obj/web-update")


def test_config_rate_limit_custom_values(monkeypatch):
    monkeypatch.setenv("APPFLOWY_BASE_URL", "https://example.test")
    monkeypatch.setenv("APPFLOWY_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("APPFLOWY_RATE_LIMIT_CALLS_PER_MINUTE", "5")
    monkeypatch.setenv("APPFLOWY_RATE_LIMIT_WRITES_PER_MINUTE", "2")
    monkeypatch.setenv("APPFLOWY_RATE_LIMIT_BLOB_COLLAB_PER_MINUTE", "1")
    monkeypatch.setenv("APPFLOWY_RATE_LIMIT_CONCURRENT_CALLS", "3")
    cfg = AppFlowyConfig.from_env()
    assert cfg.rate_limit_calls_per_minute == 5
    assert cfg.rate_limit_writes_per_minute == 2
    assert cfg.rate_limit_blob_collab_per_minute == 1
    assert cfg.rate_limit_max_concurrent == 3


# ---------------------------------------------------------------------------
# Client integration: dry-run does not trigger network rate limiter
# ---------------------------------------------------------------------------


def test_dry_run_does_not_trigger_rate_limiter():
    """Dry-run operations return without calling the network; no rate budget consumed."""
    cfg = AppFlowyConfig(
        base_url="https://example.test",
        access_token="tok",
        allow_writes=False,
        rate_limit_enabled=True,
        rate_limit_calls_per_minute=1,  # would fail on second call
    )
    from appflowy_mcp_toolkit.client import AppFlowyClient

    with AppFlowyClient(cfg) as client:
        # These are dry-run by default — they return before any network call
        r1 = client.publish_page("ws", "view", dry_run=True)
        r2 = client.publish_page("ws", "view", dry_run=True)
        r3 = client.publish_page("ws", "view", dry_run=True)

    # All three returned successfully — no rate error from dry-run
    assert r1["dry_run"] is True
    assert r2["dry_run"] is True
    assert r3["dry_run"] is True


def test_network_call_over_limit_raises():
    """A real network call past the limit raises AppFlowyError."""
    cfg = AppFlowyConfig(
        base_url="https://example.test",
        access_token="tok",
        rate_limit_enabled=True,
        rate_limit_calls_per_minute=2,
    )

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": []})

    from appflowy_mcp_toolkit.client import AppFlowyClient

    with AppFlowyClient(
        cfg, http_client=httpx.Client(transport=httpx.MockTransport(handler))
    ) as client:
        client.request("GET", "/api/workspace")
        client.request("GET", "/api/workspace")
        with pytest.raises(AppFlowyError, match="Rate limit exceeded"):
            client.request("GET", "/api/workspace")
