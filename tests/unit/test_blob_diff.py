from __future__ import annotations

import uuid

import httpx
import pytest

from appflowy_mcp_toolkit.blob_diff import (
    decode_database_blob_diff_response,
    encode_database_blob_diff_request,
)
from appflowy_mcp_toolkit.config import AppFlowyConfig
from appflowy_mcp_toolkit.errors import AppFlowySchemaError


def test_encode_database_blob_diff_request_version_only() -> None:
    assert encode_database_blob_diff_request(version=1) == b"\x10\x01"


def test_encode_database_blob_diff_request_with_max_known_rid() -> None:
    assert (
        encode_database_blob_diff_request(
            version=1,
            max_known_rid={"timestamp": 300, "seq_no": 2},
        )
        == b"\x0a\x05\x08\xac\x02\x10\x02\x10\x01"
    )


def test_decode_database_blob_diff_response_summary() -> None:
    row_id = uuid.UUID("11111111-2222-3333-4444-555555555555")
    update = _message(
        _field_bytes(1, row_id.bytes),
        _field_message(2, _field_varint(1, 12345) + _field_varint(2, 7)),
        _field_message(3, _field_bytes(1, b"doc-state") + _field_varint(2, 1)),
    )
    deleted = _message(
        _field_bytes(1, b"legacy-row-id"),
        _field_message(2, _field_varint(1, 12346) + _field_varint(2, 8)),
    )
    response = _message(
        _field_bytes(1, b"manifest-1"),
        _field_bytes(2, b"head-key"),
        _field_message(3, update),
        _field_message(4, deleted),
        _field_varint(6, 1),
        _field_varint(7, 30),
        _field_bytes(8, b"pending"),
    )

    result = decode_database_blob_diff_response(response)

    assert result["manifest_version"] == "manifest-1"
    assert result["head_blob_key"] == "head-key"
    assert result["status"] == 1
    assert result["status_name"] == "PENDING"
    assert result["retry_after_secs"] == 30
    assert result["message"] == "pending"
    assert result["counts"] == {"updates": 1, "deletes": 1, "creates": 0, "rows": 2}
    assert result["rows"][0] == {
        "operation": "update",
        "row_id": str(row_id),
        "rid": {"timestamp": 12345, "seq_no": 7},
        "doc_state_bytes": 9,
        "encoder_version": 1,
        "has_document": False,
    }
    assert result["rows"][1] == {
        "operation": "delete",
        "row_id": "legacy-row-id",
        "rid": {"timestamp": 12346, "seq_no": 8},
    }


def test_decode_database_blob_diff_rejects_truncated_length_field() -> None:
    with pytest.raises(AppFlowySchemaError, match="Truncated length-delimited"):
        decode_database_blob_diff_response(b"\x0a\x05abc")


def test_client_posts_blob_diff_binary_request() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        assert request.url.path == "/api/workspace/ws/database/db/blob/diff"
        assert request.headers["content-type"] == "application/octet-stream"
        assert request.content == b"\x10\x01"
        response = _message(_field_varint(6, 0))
        return httpx.Response(
            200,
            content=response,
            headers={"content-type": "application/octet-stream"},
        )

    from appflowy_mcp_toolkit.client import AppFlowyClient

    client = AppFlowyClient(
        AppFlowyConfig(base_url="https://example.test", access_token="test-token"),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = client.get_database_blob_diff_summary("ws", "db")

    assert result["status"] == 0
    assert result["status_name"] == "READY"
    assert result["counts"]["rows"] == 0
    assert seen[0].headers["authorization"] == "Bearer test-token"


def _message(*parts: bytes) -> bytes:
    return b"".join(parts)


def _field_varint(field_number: int, value: int) -> bytes:
    return _varint((field_number << 3) | 0) + _varint(value)


def _field_bytes(field_number: int, value: bytes) -> bytes:
    return _varint((field_number << 3) | 2) + _varint(len(value)) + value


def _field_message(field_number: int, value: bytes) -> bytes:
    return _field_bytes(field_number, value)


def _varint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)
