from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from appflowy_mcp_toolkit.typed_fields import FieldSchema, FieldType, TypedFieldError, build_cells

FIELDS: list[dict[str, Any]] = [
    {
        "id": "description_id",
        "name": "Description",
        "field_type": 0,
        "is_primary": True,
    },
    {
        "id": "status_id",
        "name": "Status",
        "field_type": 3,
        "type_option": {
            "content": {
                "options": [
                    {"id": "todo", "name": "To Do"},
                    {"id": "doing", "name": "Doing"},
                    {"id": "done", "name": "Done"},
                ]
            }
        },
    },
    {
        "id": "labels_id",
        "name": "Labels",
        "field_type": "MultiSelect",
        "options": [
            {"id": "bug", "name": "Bug"},
            {"id": "release", "name": "Release"},
        ],
    },
    {
        "id": "tasks_id",
        "name": "Tasks",
        "field_type": "Checklist",
        "type_option_data": {
            "options": [
                {"id": "write", "name": "Write docs"},
                {"id": "test", "name": "Run tests"},
            ]
        },
    },
    {"id": "points_id", "name": "Points", "field_type": 1},
    {"id": "blocked_id", "name": "Blocked", "field_type": 5},
    {"id": "link_id", "name": "Link", "field_type": 6},
    {"id": "due_id", "name": "Due", "field_type": 2},
    {"id": "time_id", "name": "Start time", "field_type": 13},
    {"id": "modified_id", "name": "Last modified", "field_type": 8},
    {"id": "relation_id", "name": "Related", "field_type": 10},
]


def test_schema_parses_fields_and_resolves_by_name_or_id() -> None:
    schema = FieldSchema(FIELDS)

    description = schema.resolve("Description")
    assert description.id == "description_id"
    assert description.field_type is FieldType.RICH_TEXT
    assert description.field_type_id == 0
    assert description.is_primary is True

    status = schema.resolve("status_id")
    assert status.name == "Status"
    assert status.field_type is FieldType.SINGLE_SELECT
    assert [(option.id, option.name) for option in status.options] == [
        ("todo", "To Do"),
        ("doing", "Doing"),
        ("done", "Done"),
    ]


def test_schema_rejects_unknown_and_duplicate_fields() -> None:
    with pytest.raises(TypedFieldError, match="Unknown field 'Missing'"):
        FieldSchema(FIELDS).resolve("Missing")

    with pytest.raises(TypedFieldError, match="Duplicate field name"):
        FieldSchema([FIELDS[0], {**FIELDS[0], "id": "other_id"}])


def test_build_cells_normalizes_common_task_fields() -> None:
    assert build_cells(
        FIELDS,
        {
            "Description": "Ship release notes",
            "Status": "doing",
            "Labels": ["Bug", "release"],
            "Tasks": [
                {"id": "write", "checked": True},
                {"name": "Run tests", "selected": False},
                "Publish",
            ],
        },
    ) == {
        "Description": "Ship release notes",
        "Status": "Doing",
        "Labels": ["Bug", "Release"],
        "Tasks": {
            "options": [
                {"id": "write", "name": "Write docs"},
                {"id": "test", "name": "Run tests"},
                {"id": "item_2", "name": "Publish"},
            ],
            "selected_option_ids": ["write"],
        },
    }


def test_build_cells_accepts_existing_checklist_shape() -> None:
    assert build_cells(
        FIELDS,
        {
            "Tasks": {
                "options": [
                    {"id": "write", "name": "Write docs"},
                    {"id": "test", "name": "Run tests"},
                ],
                "selected_option_ids": ["write", "test"],
            }
        },
    ) == {
        "Tasks": {
            "options": [
                {"id": "write", "name": "Write docs"},
                {"id": "test", "name": "Run tests"},
            ],
            "selected_option_ids": ["write", "test"],
        }
    }


def test_build_cells_validates_select_options() -> None:
    with pytest.raises(TypedFieldError, match="Invalid option for field 'Status': 'Blocked'"):
        build_cells(FIELDS, {"Status": "Blocked"})

    with pytest.raises(TypedFieldError, match="Invalid option for field 'Labels': 'missing'"):
        build_cells(FIELDS, {"Labels": ["Bug", "missing"]})

    with pytest.raises(TypedFieldError, match="selected unknown checklist option ids"):
        build_cells(
            FIELDS,
            {
                "Tasks": {
                    "options": [{"id": "known", "name": "Known"}],
                    "selected_option_ids": ["other"],
                }
            },
        )


def test_build_cells_supports_simple_scalar_types() -> None:
    now = datetime(2026, 5, 16, 12, 30)

    assert build_cells(
        FIELDS,
        {
            "Points": "13.5",
            "Blocked": False,
            "Link": "https://example.test/task",
            "Due": now,
        },
    ) == {
        "Points": 13.5,
        "Blocked": False,
        "Link": "https://example.test/task",
        "Due": "2026-05-16T12:30:00",
    }

    assert build_cells(FIELDS, {"Due": "2026-05-16"}) == {"Due": "2026-05-16"}


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("Description", 123, "expects a string"),
        ("Points", True, "expects a number, not a boolean"),
        ("Points", "NaNish", "expects a numeric string"),
        ("Blocked", "false", "expects a boolean"),
        ("Link", 123, "expects a URL string"),
        ("Link", "not-a-url", "expects an absolute URL"),
        ("Due", "not-a-date", "expects an ISO date/datetime string"),
    ],
)
def test_build_cells_validates_simple_scalar_types(field: str, value: object, message: str) -> None:
    with pytest.raises(TypedFieldError, match=message):
        build_cells(FIELDS, {field: value})


def test_build_cells_rejects_read_only_and_deferred_fields() -> None:
    with pytest.raises(TypedFieldError, match="read-only"):
        build_cells(FIELDS, {"Last modified": "2026-05-16T12:00:00Z"})

    with pytest.raises(TypedFieldError, match="not supported yet"):
        build_cells(FIELDS, {"Related": "row_123"})

    with pytest.raises(TypedFieldError, match="not supported yet"):
        build_cells(FIELDS, {"Start time": "09:15"})


def test_schema_rejects_unsupported_field_type() -> None:
    with pytest.raises(TypedFieldError, match="Unsupported field_type"):
        FieldSchema([{"id": "custom", "name": "Custom", "field_type": 999}])
