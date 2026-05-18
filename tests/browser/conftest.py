from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _disable_rate_limits_for_browser_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    # Browser tests intentionally poll AppFlowy until the web UI catches up.
    # Unit tests cover the limiter; these tests should exercise browser-visible behavior.
    monkeypatch.setenv("APPFLOWY_RATE_LIMIT_ENABLED", "false")
