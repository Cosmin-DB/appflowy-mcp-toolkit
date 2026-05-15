from __future__ import annotations

import json
from typing import Any


def to_json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False)


def compact(data: Any, *, max_chars: int = 20000) -> str:
    text = to_json(data)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 80] + "\n… truncated …"
