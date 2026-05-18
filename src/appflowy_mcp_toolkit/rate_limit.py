"""Simple token-bucket rate limiter for AppFlowy MCP in-process calls.

Each :class:`RateLimiter` instance is independent. CLI/direct clients create
one from config; the MCP server keeps a shared process-wide instance so limits
apply across tool calls.

Thread safety: uses :mod:`threading.Lock` so concurrent threads within one
process share the same bucket counts correctly.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

from .errors import AppFlowyError

# HTTP methods that count as write operations
_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Path fragments that indicate blob or collab operations
_BLOB_COLLAB_FRAGMENTS = (
    "/v1/blob/",
    "/v1/collab/",
    "/collab/",
    "/blob/",
    "/published-duplicate",
    "/append-block",
    "/web-update",
)


def _is_write(method: str) -> bool:
    return method.upper() in _WRITE_METHODS


def _is_blob_collab(path: str) -> bool:
    return any(frag in path for frag in _BLOB_COLLAB_FRAGMENTS)


@dataclass
class _Bucket:
    """Sliding-window token bucket (count of calls in the last *window_seconds*)."""

    limit: int
    window_seconds: float = 60.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)
    _timestamps: list[float] = field(default_factory=list, repr=False, compare=False)

    def check_and_record(self, label: str) -> None:
        """Raise AppFlowyError if the limit is exceeded, else record this call."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            # Purge old entries
            self._timestamps = [t for t in self._timestamps if t >= cutoff]
            if len(self._timestamps) >= self.limit:
                raise AppFlowyError(
                    f"Rate limit exceeded: {label} allows {self.limit} calls per "
                    f"{int(self.window_seconds)}s window. "
                    "Slow down, paginate, or use narrower queries. "
                    "Adjust APPFLOWY_RATE_LIMIT_* env vars to change limits."
                )
            self._timestamps.append(now)


@dataclass
class _ConcurrencySlot:
    """Simple counting semaphore for max concurrent calls."""

    limit: int
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)
    _active: int = field(default=0, repr=False, compare=False)

    def acquire(self, label: str) -> None:
        with self._lock:
            if self._active >= self.limit:
                raise AppFlowyError(
                    f"Rate limit exceeded: {label} allows {self.limit} concurrent calls. "
                    "Wait for existing calls to finish. "
                    "Adjust APPFLOWY_RATE_LIMIT_CONCURRENT_CALLS to change this limit."
                )
            self._active += 1

    def release(self) -> None:
        with self._lock:
            self._active = max(0, self._active - 1)


class RateLimiter:
    """In-process rate limiter.

    Buckets:
    - *calls*: overall network calls per minute
    - *writes*: POST/PUT/PATCH/DELETE calls per minute
    - *blob_collab*: blob/collab-path calls per minute (stricter)
    - *concurrent*: max simultaneous in-flight calls
    """

    def __init__(
        self,
        *,
        calls_per_minute: int = 0,
        writes_per_minute: int = 0,
        blob_collab_per_minute: int = 0,
        max_concurrent: int = 0,
    ) -> None:
        self._calls = _Bucket(calls_per_minute) if calls_per_minute > 0 else None
        self._writes = _Bucket(writes_per_minute) if writes_per_minute > 0 else None
        self._blob_collab = _Bucket(blob_collab_per_minute) if blob_collab_per_minute > 0 else None
        self._concurrent = _ConcurrencySlot(max_concurrent) if max_concurrent > 0 else None

    def check(self, method: str, path: str) -> None:
        """Call before issuing a network request.  Raises AppFlowyError if limited."""
        if self._calls:
            self._calls.check_and_record("overall calls per minute")
        if self._writes and _is_write(method):
            self._writes.check_and_record("write calls per minute")
        if self._blob_collab and _is_blob_collab(path):
            self._blob_collab.check_and_record("blob/collab calls per minute")
        if self._concurrent:
            self._concurrent.acquire("concurrent calls")

    def release_concurrent(self) -> None:
        """Call after a network request completes (success or error)."""
        if self._concurrent:
            self._concurrent.release()

    @classmethod
    def disabled(cls) -> RateLimiter:
        """Return a no-op limiter."""
        return cls()

    @classmethod
    def from_config(cls, config: Any) -> RateLimiter:
        """Build from an :class:`AppFlowyConfig` instance."""
        if not config.rate_limit_enabled:
            return cls.disabled()
        return cls(
            calls_per_minute=config.rate_limit_calls_per_minute,
            writes_per_minute=config.rate_limit_writes_per_minute,
            blob_collab_per_minute=config.rate_limit_blob_collab_per_minute,
            max_concurrent=config.rate_limit_max_concurrent,
        )
