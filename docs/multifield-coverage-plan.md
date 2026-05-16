# Multi-Field Coverage Plan

Goal: make database row/card tools comfortable for AI agents, not just technically
possible through raw `cells-json`.

## Current State

The MCP can create/update rows with arbitrary raw `cells` payloads and now also has
a typed layer for common database fields. The typed layer reads the database schema,
validates values by AppFlowy field type, translates human-friendly values into cell
payloads, and keeps the raw path available as an escape hatch for unsupported shapes.

Implemented entry points:

- Python client: `create_typed_database_row`, `create_typed_database_row_verified`,
  `upsert_typed_database_row`.
- CLI: `create-typed-row`, `upsert-typed-row`.
- MCP tools: `appflowy_create_typed_database_row`,
  `appflowy_upsert_typed_database_row`.

## AppFlowy Field Types

The current AppFlowy `FieldType` enum in the upstream source is:

- 0 RichText: supported via string.
- 1 Number: supported for numeric values; still needs a Docker field smoke.
- 2 DateTime: supported for ISO date/datetime values; still needs a Docker field smoke.
- 3 SingleSelect: supported by option name/id.
- 4 MultiSelect: supported by option name/id list.
- 5 Checkbox: supported for booleans; still needs a Docker field smoke.
- 6 URL: supported for absolute URL strings; still needs a Docker field smoke.
- 7 Checklist: supported for checklist items and selected/completed state.
- 8 LastEditedTime: read-only/auto-managed; rejected for writes.
- 9 CreatedTime: read-only/auto-managed; rejected for writes.
- 10 Relation: deferred; needs linked database semantics.
- 11 Summary: deferred; AI/product-specific.
- 12 Translate: deferred; AI/product-specific.
- 13 Time: supported for HH:MM / HH:MM:SS values; still needs a Docker field smoke.
- 14 Media: deferred; depends on file upload/storage semantics.

User-facing docs also mention email/phone-like field concepts in some contexts, but the
current upstream enum does not expose separate Email/Phone variants in the inspected
source. Treat those as URL/RichText variants until proven otherwise.

## Evidence From Local Docker

The seeded self-hosted To-dos database exposes:

- `RichText`: `Description`, returned as a string.
- `SingleSelect`: `Status`, returned as an option name string.
- `MultiSelect`: `Multiselect`, returned as a list of option names.
- `Checklist`: `Tasks`, returned as `{options, selected_option_ids}`.
- `LastEditedTime`: `Last modified`, returned as an ISO timestamp.

The Docker smoke test now creates and upserts rows with `Description`, `Status`,
`Multiselect`, and `Tasks`, verifies the normalized returned cells, and deletes the
rows afterwards. This is enough to prove the typed writer path against a real AppFlowy
server without touching AppFlowy official cloud.

## Implemented Work

### M1. Schema Introspection Helpers

Implemented in `src/appflowy_mcp_toolkit/typed_fields.py`:

- find field by name or id
- expose `field_type`, `field_type_id`, `is_primary`
- expose select/checklist options by name/id
- identify read-only/auto fields
- return actionable validation errors for unknown fields or wrong value types

Coverage:

- unit tests in `tests/unit/test_typed_fields.py`
- self-hosted smoke confirms seeded field metadata and writes parse correctly

### M2. Cell Builders For Common Writable Types

Implemented builders accept human-friendly values and emit AppFlowy-compatible cell
values:

- RichText: string
- Number: int/float/string numeric
- DateTime: ISO date/datetime
- SingleSelect: option name/id, validated against field options
- MultiSelect: list of option names/ids, validated against field options
- Checkbox: bool
- URL: absolute URL string
- Checklist: item list or structured options with selected/completed state
- Time: HH:MM / HH:MM:SS

Coverage:

- unit tests for valid and invalid values
- no network required for builder tests

### M3. Typed Row APIs

Implemented higher-level row tools without removing raw `cells-json`:

- `create_typed_database_row`
- `create_typed_database_row_verified`
- `upsert_typed_database_row`

Example input:

```json
{
  "Description": "Ship release notes",
  "Status": "Doing",
  "Multiselect": ["open source", "fast"],
  "Tasks": [
    {"name": "Write README", "checked": true},
    {"name": "Run Docker battery", "checked": false}
  ]
}
```

Coverage:

- dry-run output includes normalized typed cells
- write paths keep the existing `--execute` gate
- verified create/upsert returns normalized cells after the write

### M4. Docker Multi-Field Smoke

Implemented for the existing self-hosted To-dos board:

- create a row with Description, Status, Multiselect, Checklist
- upsert another row with Description, Status, Multiselect, Checklist
- verify returned cells match normalized values
- delete both rows and verify absence through the existing lifecycle cleanup path

Coverage:

- `tests/selfhosted/test_selfhosted_task_lifecycle.py`
- included in `scripts/test_all_local.sh`
- no AppFlowy official cloud required

### M5. Deferred Complex Types

Keep these out of the first multi-field release unless explicitly needed:

- Relation: needs creating or discovering a linked database and stable relation cell shape.
- Media: needs file upload/download/delete workflow and storage safety rules.
- Summary/Translate: depends on AppFlowy AI services and product configuration.
- CreatedTime/LastEditedTime: read-only verification only.

## Remaining Next Slice

The typed API is usable for real task-card work now. The remaining completeness work is
to create disposable Docker test fields beyond the seeded To-dos board and prove these
supported builders against AppFlowy end-to-end:

- Number
- Checkbox
- URL
- DateTime
- Time

That should be a separate small slice because it depends on creating/editing test
database fields in Docker, not on the typed builder architecture itself.
