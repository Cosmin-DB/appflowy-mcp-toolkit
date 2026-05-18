from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _disable_rate_limits_for_selfhosted_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    # Self-hosted tests intentionally poll collab/blob endpoints for eventual consistency.
    # Unit tests cover the limiter; these tests should exercise AppFlowy behavior.
    monkeypatch.setenv("APPFLOWY_RATE_LIMIT_ENABLED", "false")
