from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppFlowyConfig:
    base_url: str = "http://localhost"
    access_token: str | None = None
    refresh_token: str | None = None
    timeout_seconds: float = 30.0
    allow_writes: bool = False
    allow_publish_writes: bool = False

    @classmethod
    def from_env(cls) -> AppFlowyConfig:
        _truthy = {"1", "true", "yes", "on"}
        return cls(
            base_url=os.getenv("APPFLOWY_BASE_URL", cls.base_url).rstrip("/"),
            access_token=os.getenv("APPFLOWY_ACCESS_TOKEN") or None,
            refresh_token=os.getenv("APPFLOWY_REFRESH_TOKEN") or None,
            timeout_seconds=float(os.getenv("APPFLOWY_TIMEOUT_SECONDS", "30")),
            allow_writes=os.getenv("APPFLOWY_ALLOW_WRITES", "false").lower() in _truthy,
            allow_publish_writes=os.getenv("APPFLOWY_ALLOW_PUBLISH_WRITES", "false").lower()
            in _truthy,
        )

    def require_token(self) -> str:
        if not self.access_token:
            raise ValueError("APPFLOWY_ACCESS_TOKEN is required")
        return self.access_token
