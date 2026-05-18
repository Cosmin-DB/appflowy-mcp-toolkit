from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AppFlowyConfig:
    base_url: str = "http://localhost"
    access_token: str | None = None
    refresh_token: str | None = None
    timeout_seconds: float = 30.0
    allow_writes: bool = False
    allow_publish_writes: bool = False
    allow_local_file_reads: bool = False
    allowed_file_roots: tuple[str, ...] = field(default_factory=tuple)
    # Rate limiting (per-client for CLI/direct use; shared per MCP server process)
    rate_limit_enabled: bool = True
    rate_limit_calls_per_minute: int = 120
    rate_limit_writes_per_minute: int = 30
    rate_limit_blob_collab_per_minute: int = 20
    rate_limit_max_concurrent: int = 8

    @classmethod
    def from_env(cls) -> AppFlowyConfig:
        _truthy = {"1", "true", "yes", "on"}
        _falsy = {"0", "false", "no", "off"}
        raw_roots = os.getenv("APPFLOWY_ALLOWED_FILE_ROOTS", "")
        roots: tuple[str, ...] = tuple(r.strip() for r in raw_roots.split(os.pathsep) if r.strip())

        # Rate limiting: enabled by default; set APPFLOWY_RATE_LIMIT_ENABLED=false to disable
        rl_enabled_raw = os.getenv("APPFLOWY_RATE_LIMIT_ENABLED", "true").lower()
        rl_enabled = rl_enabled_raw not in _falsy

        def _int(env: str, default: int) -> int:
            try:
                return int(os.getenv(env, str(default)))
            except ValueError:
                return default

        return cls(
            base_url=os.getenv("APPFLOWY_BASE_URL", cls.base_url).rstrip("/"),
            access_token=os.getenv("APPFLOWY_ACCESS_TOKEN") or None,
            refresh_token=os.getenv("APPFLOWY_REFRESH_TOKEN") or None,
            timeout_seconds=float(os.getenv("APPFLOWY_TIMEOUT_SECONDS", "30")),
            allow_writes=os.getenv("APPFLOWY_ALLOW_WRITES", "false").lower() in _truthy,
            allow_publish_writes=os.getenv("APPFLOWY_ALLOW_PUBLISH_WRITES", "false").lower()
            in _truthy,
            allow_local_file_reads=os.getenv("APPFLOWY_ALLOW_LOCAL_FILE_READS", "false").lower()
            in _truthy,
            allowed_file_roots=roots,
            rate_limit_enabled=rl_enabled,
            rate_limit_calls_per_minute=_int("APPFLOWY_RATE_LIMIT_CALLS_PER_MINUTE", 120),
            rate_limit_writes_per_minute=_int("APPFLOWY_RATE_LIMIT_WRITES_PER_MINUTE", 30),
            rate_limit_blob_collab_per_minute=_int(
                "APPFLOWY_RATE_LIMIT_BLOB_COLLAB_PER_MINUTE", 20
            ),
            rate_limit_max_concurrent=_int("APPFLOWY_RATE_LIMIT_CONCURRENT_CALLS", 8),
        )

    def require_token(self) -> str:
        if not self.access_token:
            raise ValueError("APPFLOWY_ACCESS_TOKEN is required")
        return self.access_token
