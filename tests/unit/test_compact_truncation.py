"""Tests for compact() output validity and truncation behaviour."""

from __future__ import annotations

import json

from appflowy_mcp_toolkit.formatting import compact


def test_small_dict_is_valid_json():
    result = compact({"key": "value", "n": 42})
    parsed = json.loads(result)
    assert parsed == {"key": "value", "n": 42}


def test_small_list_is_valid_json():
    result = compact([1, 2, 3])
    parsed = json.loads(result)
    assert parsed == [1, 2, 3]


def test_no_truncation_below_limit():
    data = {"a": "b"}
    result = compact(data, max_chars=10000)
    assert "truncated" not in result or json.loads(result).get("truncated") is not True


def test_large_object_returns_valid_json():
    big = {"rows": [{"id": i, "text": "x" * 200} for i in range(200)]}
    result = compact(big, max_chars=1000)
    parsed = json.loads(result)  # must not raise
    assert isinstance(parsed, dict)


def test_truncated_response_has_truncated_true():
    big = {"rows": [{"id": i, "text": "x" * 200} for i in range(200)]}
    result = compact(big, max_chars=1000)
    parsed = json.loads(result)
    assert parsed["truncated"] is True


def test_truncated_response_has_max_chars():
    big = {"rows": [{"id": i} for i in range(500)]}
    result = compact(big, max_chars=500)
    parsed = json.loads(result)
    assert parsed["max_chars"] == 500


def test_truncated_output_length_controlled():
    big = {"rows": ["x" * 500 for _ in range(100)]}
    result = compact(big, max_chars=2000)
    assert len(result) <= 2000


def test_truncated_output_length_controlled_with_escaped_preview():
    big = {"rows": ['"quoted"\\value' * 100 for _ in range(100)]}
    result = compact(big, max_chars=2000)
    assert len(result) <= 2000
    assert json.loads(result)["truncated"] is True


def test_truncated_original_chars_reflects_full_size():
    big = {"data": "y" * 50000}
    full = len(__import__("json").dumps(big, indent=2, ensure_ascii=False))
    result = compact(big, max_chars=1000)
    parsed = json.loads(result)
    assert parsed["original_chars"] == full


def test_full_oversized_payload_not_emitted():
    payload = "z" * 30000
    result = compact({"data": payload}, max_chars=500)
    assert len(result) < 10000  # far less than the full payload


def test_truncated_has_guidance():
    big = {"x": "a" * 50000}
    result = compact(big, max_chars=200)
    parsed = json.loads(result)
    assert "guidance" in parsed
    assert len(parsed["guidance"]) > 10


def test_truncated_preview_is_string():
    big = {"x": "b" * 50000}
    result = compact(big, max_chars=500)
    parsed = json.loads(result)
    assert isinstance(parsed.get("preview"), str)


def test_exact_limit_not_truncated():
    data = {"k": "v"}
    text = __import__("json").dumps(data, indent=2, ensure_ascii=False, sort_keys=False)
    result = compact(data, max_chars=len(text))
    assert json.loads(result) == data


def test_one_char_below_limit_not_truncated():
    data = {"k": "v"}
    text = __import__("json").dumps(data, indent=2, ensure_ascii=False, sort_keys=False)
    result = compact(data, max_chars=len(text) + 1)
    assert json.loads(result) == data


def test_very_small_max_chars_still_valid_json():
    big = {"data": "c" * 10000}
    result = compact(big, max_chars=100)
    parsed = json.loads(result)  # must not raise
    assert parsed["truncated"] is True
