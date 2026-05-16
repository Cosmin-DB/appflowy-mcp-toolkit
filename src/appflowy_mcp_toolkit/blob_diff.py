from __future__ import annotations

import uuid
from typing import Any

from .errors import AppFlowySchemaError


def encode_database_blob_diff_request(
    *,
    version: int = 1,
    max_known_rid: dict[str, int] | None = None,
) -> bytes:
    """Encode AppFlowy Web's DatabaseBlobDiffRequest protobuf message.

    The browser sends this message to the database blob/diff endpoint with
    Content-Type: application/octet-stream. The schema is small enough that a
    minimal protobuf encoder is clearer than adding generated code.
    """
    out = bytearray()
    if max_known_rid is not None:
        rid = bytearray()
        rid += _key(1, 0)
        rid += _varint(int(max_known_rid["timestamp"]))
        rid += _key(2, 0)
        rid += _varint(int(max_known_rid["seq_no"]))
        out += _key(1, 2)
        out += _length_delimited(bytes(rid))
    out += _key(2, 0)
    out += _varint(version)
    return bytes(out)


def decode_database_blob_diff_response(payload: bytes) -> dict[str, Any]:
    """Decode enough of DatabaseBlobDiffResponse for safe diagnostics.

    The returned structure intentionally omits raw doc-state bytes. It keeps
    row ids, operation type, RID values and byte sizes, which is enough to
    answer whether a row is available through the same blob/diff path used by
    AppFlowy Web.
    """
    fields = _read_fields(payload)
    updates = [_decode_row_update(item) for item in fields.get(3, [])]
    deletes = [_decode_row_delete(item) for item in fields.get(4, [])]
    creates = [_decode_row_update(item) for item in fields.get(5, [])]

    rows: list[dict[str, Any]] = []
    rows.extend({"operation": "update", **item} for item in updates)
    rows.extend({"operation": "delete", **item} for item in deletes)
    rows.extend({"operation": "create", **item} for item in creates)

    status_values = fields.get(6, [])
    # Protobuf enum fields default to the first enum value when absent. In the
    # generated AppFlowy Web bundle, DiffStatus.READY is 0.
    status = status_values[-1] if status_values else 0
    return {
        "manifest_version": _last_text(fields, 1),
        "head_blob_key": _last_text(fields, 2),
        "status": status,
        "status_name": {0: "READY", 1: "PENDING"}.get(status, "UNKNOWN"),
        "retry_after_secs": _last_int(fields, 7),
        "message": _last_text(fields, 8),
        "counts": {
            "updates": len(updates),
            "deletes": len(deletes),
            "creates": len(creates),
            "rows": len(rows),
        },
        "rows": rows,
    }


def _decode_row_update(payload: bytes) -> dict[str, Any]:
    fields = _read_fields(payload)
    row: dict[str, Any] = {
        "row_id": _decode_row_id(_last_bytes(fields, 1)),
        "rid": _decode_rid(_last_bytes(fields, 2)),
        "doc_state_bytes": None,
        "encoder_version": None,
        "has_document": bool(fields.get(4)),
    }
    doc_state_payload = _last_bytes(fields, 3)
    if doc_state_payload is not None:
        doc_state = _read_fields(doc_state_payload)
        row["doc_state_bytes"] = len(_last_bytes(doc_state, 1) or b"")
        row["encoder_version"] = _last_int(doc_state, 2)
    return row


def _decode_row_delete(payload: bytes) -> dict[str, Any]:
    fields = _read_fields(payload)
    return {
        "row_id": _decode_row_id(_last_bytes(fields, 1)),
        "rid": _decode_rid(_last_bytes(fields, 2)),
    }


def _decode_rid(payload: bytes | None) -> dict[str, int] | None:
    if payload is None:
        return None
    fields = _read_fields(payload)
    timestamp = _last_int(fields, 1)
    seq_no = _last_int(fields, 2)
    if timestamp is None and seq_no is None:
        return None
    return {"timestamp": int(timestamp or 0), "seq_no": int(seq_no or 0)}


def _decode_row_id(payload: bytes | None) -> str | None:
    if payload is None:
        return None
    if len(payload) == 16:
        return str(uuid.UUID(bytes=payload))
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError:
        return payload.hex()


def _read_fields(payload: bytes) -> dict[int, list[Any]]:
    pos = 0
    out: dict[int, list[Any]] = {}
    while pos < len(payload):
        tag, pos = _read_varint(payload, pos)
        field_number = tag >> 3
        wire_type = tag & 0x07
        if field_number <= 0:
            raise AppFlowySchemaError("Invalid protobuf field number in blob/diff payload")
        value: Any
        if wire_type == 0:
            value, pos = _read_varint(payload, pos)
        elif wire_type == 2:
            length, pos = _read_varint(payload, pos)
            end = pos + length
            if end > len(payload):
                raise AppFlowySchemaError("Truncated length-delimited blob/diff field")
            value = payload[pos:end]
            pos = end
        else:
            raise AppFlowySchemaError(
                f"Unsupported protobuf wire type {wire_type} in blob/diff payload"
            )
        out.setdefault(field_number, []).append(value)
    return out


def _read_varint(payload: bytes, pos: int) -> tuple[int, int]:
    shift = 0
    value = 0
    while pos < len(payload):
        byte = payload[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, pos
        shift += 7
        if shift > 70:
            raise AppFlowySchemaError("Invalid varint in blob/diff payload")
    raise AppFlowySchemaError("Truncated varint in blob/diff payload")


def _key(field_number: int, wire_type: int) -> bytes:
    return _varint((field_number << 3) | wire_type)


def _length_delimited(payload: bytes) -> bytes:
    return _varint(len(payload)) + payload


def _varint(value: int) -> bytes:
    if value < 0:
        raise ValueError("protobuf varint value must be non-negative")
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def _last_bytes(fields: dict[int, list[Any]], field_number: int) -> bytes | None:
    values = fields.get(field_number) or []
    value = values[-1] if values else None
    return value if isinstance(value, bytes) else None


def _last_int(fields: dict[int, list[Any]], field_number: int) -> int | None:
    values = fields.get(field_number) or []
    value = values[-1] if values else None
    return value if isinstance(value, int) else None


def _last_text(fields: dict[int, list[Any]], field_number: int) -> str | None:
    value = _last_bytes(fields, field_number)
    if value is None:
        return None
    try:
        return value.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AppFlowySchemaError("blob/diff response contained invalid UTF-8 text") from exc
