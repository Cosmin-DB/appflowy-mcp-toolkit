from __future__ import annotations

from typing import Any

import httpx


def json_response(
    data: Any, status_code: int = 200, headers: dict[str, str] | None = None
) -> httpx.Response:
    return httpx.Response(status_code, json=data, headers=headers)
