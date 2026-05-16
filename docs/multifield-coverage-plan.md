# Multi-Field Coverage Plan

Goal: make database row/card tools comfortable for AI agents, not just technically
possible through raw `cells-json`.

## Current State

The MCP can already create/update rows with arbitrary `cells` payloads. That is a
low-level escape hatch: it works when the caller already knows the exact AppFlowy cell
shape.

What is missing is a typed layer that reads the database schema, validates values by
field type, translates human-friendly values into AppFlowy cell payloads, and verifies
the resulting row against real AppFlowy.

## AppFlowy Field Types

The current AppFlowy `FieldType` enum in the upstream source is:

- 0 RichText: supported via string; add validation/normalization.
- 1 Number: add builder plus Docker smoke.
- 2 DateTime: add builder plus Docker smoke.
- 3 SingleSelect: partially supported for `Status`; generalize by field.
- 4 MultiSelect: add builder plus Docker smoke.
- 5 Checkbox: add builder plus Docker smoke.
- 6 URL: add builder plus Docker smoke.
- 7 Checklist: add builder plus Docker smoke.
- 8 LastEditedTime: read/verify only; auto-managed.
- 9 CreatedTime: read/verify only; auto-managed.
- 10 Relation: defer; needs linked database semantics.
- 11 Summary: defer; AI/product-specific.
- 12 Translate: defer; AI/product-specific.
- 13 Time: add after DateTime if route supports it.
- 14 Media: defer; depends on file upload/storage semantics.

User-facing docs also mention email/phone-like field concepts in some contexts, but the
current upstream enum does not expose separate Email/Phone variants in the inspected
source. Treat those as possible URL/RichText variants until proven otherwise.

## Evidence From Local Docker

The seeded self-hosted To-dos database currently exposes:

- `RichText`: `Description`, returned as a string.
- `SingleSelect`: `Status`, returned as an option name string.
- `MultiSelect`: `Multiselect`, returned as a list of option names.
- `Checklist`: `Tasks`, returned as `{options, selected_option_ids}`.
- `LastEditedTime`: `Last modified`, returned as an ISO timestamp.

This is enough to build the first typed writer tests without needing AppFlowy official
cloud.

## Proposed Work

### M1. Schema Introspection Helpers

Add a small schema module that turns `list_database_fields` into typed field metadata:

- find field by name or id
- expose `field_type`, `field_type_id`, `is_primary`
- expose select/checklist options by name/id
- identify read-only/auto fields
- return actionable validation errors for unknown fields or wrong value types

Acceptance:

- unit tests for schema parsing
- self-hosted read smoke confirms all seeded field metadata is parsed

### M2. Cell Builders For Common Writable Types

Add builders that accept human-friendly values and emit AppFlowy-compatible cell values:

- RichText: string
- Number: int/float/string numeric
- DateTime: ISO date/datetime, optional timezone handling
- SingleSelect: option name/id, validate against field options
- MultiSelect: list of option names/ids, validate all options
- Checkbox: bool
- URL: URL string plus any server-required object shape if needed
- Checklist: list of items plus selected/completed flags
- Time: HH:MM / HH:MM:SS if supported by current API

Acceptance:

- unit tests for valid/invalid values
- no network required for pure builder tests

### M3. Typed Row APIs

Add higher-level row tools without removing raw `cells-json`:

- `create_typed_database_row`
- `update_typed_database_row`
- possibly `create_typed_task` / `update_typed_task` as wrappers over the same builder

Input should be stable and AI-friendly, for example:

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

Acceptance:

- dry-run output shows resolved field types and normalized cell payload
- real writes require existing write gates
- verification returns normalized cells after create/update

### M4. Docker Multi-Field Smoke

Use the existing self-hosted To-dos board first:

- create a row with Description, Status, Multiselect, Checklist
- update Status, Multiselect, Checklist
- verify returned cells match normalized values
- delete row and verify absence

Then create a disposable test database/view or field set for types not present in the
seeded board:

- Number
- Checkbox
- URL
- DateTime
- Time if supported

Acceptance:

- `scripts/test_all_local.sh` includes these tests
- no AppFlowy official cloud required

### M5. Deferred Complex Types

Keep these out of the first multi-field release unless explicitly needed:

- Relation: needs creating or discovering a linked database and stable relation cell shape.
- Media: needs file upload/download/delete workflow and storage safety rules.
- Summary/Translate: depends on AppFlowy AI services and product configuration.
- CreatedTime/LastEditedTime: read-only verification only.

## Recommended Next Slice

Start with M1 + M2 for the field types already present in the Docker seed:

- RichText
- SingleSelect
- MultiSelect
- Checklist

Then add M4 smoke for those fields. This gives immediate value for real task cards
without opening the more fragile Number/Date/Media/Relation surface yet.
