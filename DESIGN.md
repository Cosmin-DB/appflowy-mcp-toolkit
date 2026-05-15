# Design

The toolkit is intentionally small and layered.

```text
AppFlowy REST API
  ↑
HTTP client + auth + errors
  ↑
Domain services: workspaces, folders, databases, rows
  ↑                 ↑
CLI inspection      MCP tools (read-only + opt-in writes)
```

## Principles

- Read-only first.
- Explicit IDs over magic defaults.
- Treat AppFlowy IDs as opaque strings.
- Keep public repo generic; private workflows live outside it.
- No secrets in repo, logs, fixtures, or test output.
- Prefer boring Python over clever abstractions.

## Auth

The initial client uses bearer tokens from environment variables. Refresh-token support is
implemented in the HTTP layer when `APPFLOWY_REFRESH_TOKEN` is present, but no token is
written back to disk by default.

## Write safety

Write tools are included but off by default. Two independent gates must be cleared for a
real mutation to occur:

1. The caller must pass `dry_run=False` to the client method or MCP tool.
2. The environment variable `APPFLOWY_ALLOW_WRITES=true` must be set.

Dry-run calls return the would-be HTTP method, path, and payload without touching the API.
No broad destructive operations (row delete, view delete, bulk actions) are included; no
confirmed public REST endpoints exist for them, and they are out of scope for this release.

## pre_hash and MCP-managed task upserts

`pre_hash` is used exclusively for MCP-managed idempotent task upserts
(`upsert_managed_task`, `move_managed_task_status`). The caller supplies a stable
`task_key` string; the client passes it as `pre_hash` in the PUT body so the same logical
task can be created-or-updated without knowing the internal AppFlowy row ID.

This pattern is tested and works against the current AppFlowy Cloud API. The precise
server-side semantics of `pre_hash` (e.g. whether it is a true idempotency key or a
content hash) are not part of the public API documentation, so this toolkit deliberately
limits its use to this one controlled pattern rather than exposing it as a general feature.

## API namespace

The toolkit targets the `/api/workspace/...` endpoints documented in the public AppFlowy
OpenAPI spec.

`POST /api/v1/workspace/get_folder` was live-tested against `beta.appflowy.cloud` and
returned 404; it is not implemented. Other `/api/v1/...` row and view endpoints
(row/create, row/update, row/delete, view/delete, view/update) are also not implemented:
they are absent from the official public OpenAPI and require official documentation plus
independent live verification before any implementation is attempted. See ROADMAP for the
deferred note.
