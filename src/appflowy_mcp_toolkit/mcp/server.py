from __future__ import annotations

import threading
from typing import Annotated, Any

from appflowy_mcp_toolkit.client import AppFlowyClient
from appflowy_mcp_toolkit.config import AppFlowyConfig
from appflowy_mcp_toolkit.formatting import compact
from appflowy_mcp_toolkit.rate_limit import RateLimiter

try:
    from mcp.server.fastmcp import FastMCP
    from mcp.types import CallToolResult, TextContent
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Install MCP extras with: python -m pip install -e '.[mcp]'") from exc

mcp = FastMCP("appflowy-mcp-toolkit")
StructuredToolResult = Annotated[CallToolResult, dict[str, Any]]
_RateLimitKey = tuple[bool, int, int, int, int]
_server_rate_limiter_lock = threading.Lock()
_server_rate_limiters: dict[_RateLimitKey, RateLimiter] = {}


def _client() -> AppFlowyClient:
    config = AppFlowyConfig.from_env()
    return AppFlowyClient(config, rate_limiter=_server_rate_limiter(config))


def _server_rate_limiter(config: AppFlowyConfig) -> RateLimiter:
    """Return the MCP process-wide limiter for the active rate-limit config."""
    if not config.rate_limit_enabled:
        return RateLimiter.disabled()

    key: _RateLimitKey = (
        config.rate_limit_enabled,
        config.rate_limit_calls_per_minute,
        config.rate_limit_writes_per_minute,
        config.rate_limit_blob_collab_per_minute,
        config.rate_limit_max_concurrent,
    )
    with _server_rate_limiter_lock:
        limiter = _server_rate_limiters.get(key)
        if limiter is None:
            limiter = RateLimiter.from_config(config)
            _server_rate_limiters[key] = limiter
        return limiter


def _structured(data: Any) -> StructuredToolResult:
    """Return backwards-compatible text plus MCP structuredContent."""
    structured_content = data if isinstance(data, dict) else {"result": data}
    return CallToolResult(
        content=[TextContent(type="text", text=compact(data))],
        structuredContent=structured_content,
    )


def main() -> None:
    mcp.run()


# Import tool modules for decorator registration. Keep these imports at module end
# so shared helpers above are initialized before tool modules import them.
from appflowy_mcp_toolkit.mcp.tools import core as _core_tools  # noqa: F401,E402
from appflowy_mcp_toolkit.mcp.tools import databases as _database_tools  # noqa: F401,E402
from appflowy_mcp_toolkit.mcp.tools import diagnostics as _diagnostic_tools  # noqa: F401,E402
from appflowy_mcp_toolkit.mcp.tools import pages as _page_tools  # noqa: F401,E402
from appflowy_mcp_toolkit.mcp.tools import publishing as _publishing_tools  # noqa: F401,E402
from appflowy_mcp_toolkit.mcp.tools import spaces_files as _space_file_tools  # noqa: F401,E402
from appflowy_mcp_toolkit.mcp.tools import tasks_rows as _task_row_tools  # noqa: F401,E402
from appflowy_mcp_toolkit.mcp.tools import templates as _template_tools  # noqa: F401,E402

if __name__ == "__main__":
    main()
