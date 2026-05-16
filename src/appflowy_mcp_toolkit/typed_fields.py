from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from urllib.parse import urlparse

from .errors import AppFlowyError


class TypedFieldError(AppFlowyError, ValueError):
    """Raised when a field schema or human cell value cannot be normalized."""


class FieldType(Enum):
    RICH_TEXT = 0
    NUMBER = 1
    DATE_TIME = 2
    SINGLE_SELECT = 3
    MULTI_SELECT = 4
    CHECKBOX = 5
    URL = 6
    CHECKLIST = 7
    LAST_EDITED_TIME = 8
    CREATED_TIME = 9
    RELATION = 10
    SUMMARY = 11
    TRANSLATE = 12
    TIME = 13
    MEDIA = 14


FIELD_TYPE_NAMES = {
    "richtext": FieldType.RICH_TEXT,
    "rich_text": FieldType.RICH_TEXT,
    "rich text": FieldType.RICH_TEXT,
    "number": FieldType.NUMBER,
    "datetime": FieldType.DATE_TIME,
    "date_time": FieldType.DATE_TIME,
    "date time": FieldType.DATE_TIME,
    "date": FieldType.DATE_TIME,
    "singleselect": FieldType.SINGLE_SELECT,
    "single_select": FieldType.SINGLE_SELECT,
    "single select": FieldType.SINGLE_SELECT,
    "select": FieldType.SINGLE_SELECT,
    "multiselect": FieldType.MULTI_SELECT,
    "multi_select": FieldType.MULTI_SELECT,
    "multi select": FieldType.MULTI_SELECT,
    "checkbox": FieldType.CHECKBOX,
    "url": FieldType.URL,
    "checklist": FieldType.CHECKLIST,
    "lasteditedtime": FieldType.LAST_EDITED_TIME,
    "last_edited_time": FieldType.LAST_EDITED_TIME,
    "last edited time": FieldType.LAST_EDITED_TIME,
    "createdtime": FieldType.CREATED_TIME,
    "created_time": FieldType.CREATED_TIME,
    "created time": FieldType.CREATED_TIME,
    "relation": FieldType.RELATION,
    "summary": FieldType.SUMMARY,
    "translate": FieldType.TRANSLATE,
    "time": FieldType.TIME,
    "media": FieldType.MEDIA,
}

READ_ONLY_TYPES = {FieldType.LAST_EDITED_TIME, FieldType.CREATED_TIME}
DEFERRED_TYPES = {
    FieldType.RELATION,
    FieldType.MEDIA,
    FieldType.SUMMARY,
    FieldType.TRANSLATE,
    FieldType.TIME,
}


@dataclass(frozen=True)
class FieldOption:
    id: str
    name: str


@dataclass(frozen=True)
class Field:
    id: str
    name: str
    field_type: FieldType
    is_primary: bool = False
    options: tuple[FieldOption, ...] = ()

    @property
    def field_type_id(self) -> int:
        return self.field_type.value

    @property
    def type(self) -> str:
        return self.field_type.name

    def option_by_name_or_id(self, value: str) -> FieldOption:
        for option in self.options:
            if value == option.name or value == option.id:
                return option
        valid = ", ".join(option.name for option in self.options) or "<none>"
        raise TypedFieldError(
            f"Invalid option for field {self.name!r}: {value!r}. Valid options: {valid}"
        )


class FieldSchema:
    def __init__(self, fields: Iterable[Mapping[str, Any]]) -> None:
        parsed = tuple(_parse_field(field) for field in fields)
        self.fields = parsed
        self._by_name = _unique_index(parsed, "name")
        self._by_id = _unique_index(parsed, "id")

    def resolve(self, name_or_id: str) -> Field:
        if name_or_id in self._by_name:
            return self._by_name[name_or_id]
        if name_or_id in self._by_id:
            return self._by_id[name_or_id]
        available = ", ".join(field.name for field in self.fields) or "<none>"
        raise TypedFieldError(f"Unknown field {name_or_id!r}. Available fields: {available}")


def build_cells(
    fields: Iterable[Mapping[str, Any]] | FieldSchema, values: Mapping[str, Any]
) -> dict[str, Any]:
    schema = fields if isinstance(fields, FieldSchema) else FieldSchema(fields)
    cells: dict[str, Any] = {}
    for field_ref, value in values.items():
        field = schema.resolve(str(field_ref))
        _ensure_writable(field)
        cells[field.name] = _build_cell(field, value)
    return cells


def _parse_field(raw: Mapping[str, Any]) -> Field:
    field_id = _first_str(raw, ("id", "field_id")) or ""
    name = _first_str(raw, ("name", "field_name"))
    if not name:
        raise TypedFieldError(f"Field is missing a name: {raw!r}")
    field_type = _parse_field_type(raw)
    return Field(
        id=field_id,
        name=name,
        field_type=field_type,
        is_primary=bool(raw.get("is_primary", raw.get("primary", False))),
        options=tuple(_parse_options(raw)),
    )


def _parse_field_type(raw: Mapping[str, Any]) -> FieldType:
    value = raw.get("field_type", raw.get("type", raw.get("type_id")))
    if isinstance(value, bool) or value is None:
        raise TypedFieldError(f"Field {raw.get('name')!r} is missing field_type")
    if isinstance(value, int):
        try:
            return FieldType(value)
        except ValueError as exc:
            raise TypedFieldError(
                f"Unsupported field_type id for field {raw.get('name')!r}: {value}"
            ) from exc
    if isinstance(value, str):
        key = value.replace("-", "_").strip().lower()
        if key in FIELD_TYPE_NAMES:
            return FIELD_TYPE_NAMES[key]
        if key.isdigit():
            return FieldType(int(key))
    raise TypedFieldError(f"Unsupported field_type for field {raw.get('name')!r}: {value!r}")


def _parse_options(raw: Mapping[str, Any]) -> list[FieldOption]:
    option_items = _find_option_items(raw)
    options: list[FieldOption] = []
    for index, item in enumerate(option_items):
        if not isinstance(item, Mapping):
            continue
        name = _first_str(item, ("name", "title", "label"))
        option_id = _first_str(item, ("id", "option_id")) or name
        if name:
            options.append(FieldOption(id=option_id or f"option_{index}", name=name))
    return options


def _find_option_items(raw: Mapping[str, Any]) -> Sequence[Any]:
    candidates = [
        raw.get("options"),
        _nested(raw, ("type_option", "content", "options")),
        _nested(raw, ("type_option", "options")),
        _nested(raw, ("type_option_data", "options")),
        _nested(raw, ("type_option_data", "content", "options")),
    ]
    for candidate in candidates:
        if isinstance(candidate, Sequence) and not isinstance(candidate, (str, bytes, bytearray)):
            return candidate
    return ()


def _build_cell(field: Field, value: Any) -> Any:
    match field.field_type:
        case FieldType.RICH_TEXT:
            if not isinstance(value, str):
                raise TypedFieldError(f"Field {field.name!r} expects a string")
            return value
        case FieldType.NUMBER:
            return _build_number(field, value)
        case FieldType.DATE_TIME:
            return _build_datetime(field, value)
        case FieldType.SINGLE_SELECT:
            if not isinstance(value, str):
                raise TypedFieldError(f"Field {field.name!r} expects an option name or id string")
            return field.option_by_name_or_id(value).name
        case FieldType.MULTI_SELECT:
            if isinstance(value, str) or not isinstance(value, Sequence):
                raise TypedFieldError(f"Field {field.name!r} expects a list of option names or ids")
            return [field.option_by_name_or_id(str(item)).name for item in value]
        case FieldType.CHECKBOX:
            if not isinstance(value, bool):
                raise TypedFieldError(f"Field {field.name!r} expects a boolean")
            return value
        case FieldType.URL:
            if not isinstance(value, str):
                raise TypedFieldError(f"Field {field.name!r} expects a URL string")
            parsed = urlparse(value)
            if not parsed.scheme or not parsed.netloc:
                raise TypedFieldError(f"Field {field.name!r} expects an absolute URL")
            return value
        case FieldType.CHECKLIST:
            return _build_checklist(field, value)
        case _:
            _ensure_writable(field)
            raise TypedFieldError(f"Unsupported field type for field {field.name!r}: {field.type}")


def _build_number(field: Field, value: Any) -> int | float:
    if isinstance(value, bool):
        raise TypedFieldError(f"Field {field.name!r} expects a number, not a boolean")
    if isinstance(value, int | float):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise TypedFieldError(f"Field {field.name!r} expects a number")
        try:
            number = float(text) if any(char in text.lower() for char in (".", "e")) else int(text)
        except ValueError as exc:
            raise TypedFieldError(f"Field {field.name!r} expects a numeric string") from exc
        return number
    raise TypedFieldError(f"Field {field.name!r} expects a number")


def _build_datetime(field: Field, value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise TypedFieldError(f"Field {field.name!r} expects an ISO date/datetime string")
        _validate_iso_datetimeish(field, text)
        return text
    raise TypedFieldError(f"Field {field.name!r} expects an ISO date/datetime string")


def _build_checklist(field: Field, value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        options_value = value.get("options")
        selected_value = value.get("selected_option_ids", value.get("selected", ()))
        if not isinstance(options_value, Sequence) or isinstance(
            options_value, (str, bytes, bytearray)
        ):
            raise TypedFieldError(f"Field {field.name!r} expects checklist options as a list")
        options = [
            _checklist_option_from_item(field, item, index)
            for index, item in enumerate(options_value)
        ]
        selected_ids = [
            str(item) for item in _require_sequence(field, selected_value, "selected_option_ids")
        ]
        option_ids = {option["id"] for option in options}
        unknown = [item for item in selected_ids if item not in option_ids]
        if unknown:
            raise TypedFieldError(
                f"Field {field.name!r} selected unknown checklist option ids: {unknown}"
            )
        return {"options": options, "selected_option_ids": selected_ids}

    items = _require_sequence(field, value, "checklist items")
    options = []
    selected: list[str] = []
    for index, item in enumerate(items):
        option = _checklist_option_from_item(field, item, index)
        options.append(option)
        if isinstance(item, Mapping) and bool(item.get("checked", item.get("selected", False))):
            selected.append(option["id"])
    return {"options": options, "selected_option_ids": selected}


def _checklist_option_from_item(field: Field, item: Any, index: int) -> dict[str, str]:
    if isinstance(item, str):
        existing = _maybe_existing_option(field, item)
        return (
            {"id": existing.id, "name": existing.name}
            if existing
            else {"id": f"item_{index}", "name": item}
        )
    if isinstance(item, Mapping):
        name = _first_str(item, ("name", "title", "label"))
        option_id = _first_str(item, ("id", "option_id"))
        if name is None and option_id is not None:
            existing = field.option_by_name_or_id(option_id)
            name = existing.name
            option_id = existing.id
        if name is None:
            raise TypedFieldError(f"Field {field.name!r} checklist item is missing a name")
        if option_id is None:
            existing = _maybe_existing_option(field, name)
            option_id = existing.id if existing else f"item_{index}"
        return {"id": option_id, "name": name}
    raise TypedFieldError(f"Field {field.name!r} checklist items must be strings or objects")


def _ensure_writable(field: Field) -> None:
    if field.field_type in READ_ONLY_TYPES:
        raise TypedFieldError(
            f"Field {field.name!r} ({field.type}) is read-only and cannot be written"
        )
    if field.field_type in DEFERRED_TYPES:
        raise TypedFieldError(
            f"Field {field.name!r} ({field.type}) is not supported yet; this field type is deferred"
        )


def _validate_iso_datetimeish(field: Field, value: str) -> None:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return
    except ValueError:
        pass
    try:
        datetime.fromisoformat(f"{value}T00:00:00")
    except ValueError as exc:
        raise TypedFieldError(f"Field {field.name!r} expects an ISO date/datetime string") from exc


def _require_sequence(field: Field, value: Any, label: str) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    raise TypedFieldError(f"Field {field.name!r} expects {label} as a list")


def _maybe_existing_option(field: Field, value: str) -> FieldOption | None:
    for option in field.options:
        if value == option.name or value == option.id:
            return option
    return None


def _unique_index(fields: Sequence[Field], attr: str) -> dict[str, Field]:
    indexed: dict[str, Field] = {}
    for field in fields:
        key = getattr(field, attr)
        if not key:
            continue
        if key in indexed:
            raise TypedFieldError(f"Duplicate field {attr}: {key!r}")
        indexed[key] = field
    return indexed


def _first_str(raw: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        value = raw.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _nested(raw: Mapping[str, Any], keys: Sequence[str]) -> Any:
    current: Any = raw
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current
