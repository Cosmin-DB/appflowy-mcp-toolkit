from __future__ import annotations

import json
from typing import Any


def to_json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False)


def compact(data: Any, *, max_chars: int = 20000) -> str:
    """Serialize *data* to compact JSON, hard-capping at *max_chars* characters.

    When the serialized form fits within *max_chars* the output is normal JSON
    and is parseable as-is.

    When it would exceed the limit, the function returns a **valid JSON object**
    (never a truncated raw substring) with the following shape::

        {
          "truncated": true,
          "max_chars": <limit>,
          "original_chars": <full serialized length>,
          "preview": "<first N chars of the serialized form>",
          "guidance": "Use limit/ids/pagination or a narrower query to fetch a smaller slice."
        }

    The *preview* field is informational only and is clearly labelled; agents
    and humans should not attempt to parse it as complete data.
    """
    text = to_json(data)
    if len(text) <= max_chars:
        return text

    # How many preview chars can we afford?  The preview is itself JSON-encoded
    # inside the envelope, so escaping can expand it.  Trim iteratively instead
    # of assuming one source character equals one output character.
    guidance = "Use limit/ids/pagination or a narrower query to fetch a smaller slice."
    envelope_template = {
        "truncated": True,
        "max_chars": max_chars,
        "original_chars": len(text),
        "preview": "",
        "guidance": guidance,
    }
    envelope_base = to_json(envelope_template)
    preview_budget = max(0, max_chars - len(envelope_base))

    while True:
        result = {
            "truncated": True,
            "max_chars": max_chars,
            "original_chars": len(text),
            "preview": text[:preview_budget],
            "guidance": guidance,
        }
        result_text = to_json(result)
        if len(result_text) <= max_chars or preview_budget == 0:
            return result_text
        overshoot = len(result_text) - max_chars
        preview_budget = max(0, preview_budget - max(1, overshoot))
