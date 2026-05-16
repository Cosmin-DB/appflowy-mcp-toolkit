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
Row delete and arbitrary existing-row updates by `row_id` are available only through
the experimental Yjs collab path (see below).
Page/view trash, restore, and delete-from-trash operations are included behind the same
dry-run/write gate model. Workspace admin/member/invite/publish/import operations are
not included in the first release candidate.

## Collab diagnostics

The toolkit includes read-only collab inspection helpers for database documents:

- `get_collab_json` fetches the JSON representation of a collab object through
  `/api/workspace/v1/{workspace_id}/collab/{object_id}/json`.
- `get_database_row_orders` extracts per-view `row_orders` from the database collab.

These diagnostics exist because AppFlowy Web board operations are backed by Yjs/AppFlowy
collab state. They are intentionally read-only and do not perform binary collab writes.

## Experimental: Yjs-based row update/delete

AppFlowy Web does not expose REST endpoints for every row mutation. Deletion is a Yjs collab
mutation: the row ID is removed from every view's `row_orders` YArray in one transaction,
and the incremental lib0-v1 update is posted to
`/api/workspace/v1/{workspace_id}/collab/{database_id}/web-update`.

Existing manual/UI-created rows have the same issue for updates: REST `PUT /row`
targets a deterministic row derived from `pre_hash`, not an arbitrary existing
`row_id`. For those rows, the toolkit updates the row's `DatabaseRow` collab
document by mutating `data.cells.<field_id>.data` and posting the incremental update
to `/api/workspace/v1/{workspace_id}/collab/{row_id}/web-update` with collab type
`DatabaseRow`.

The toolkit implements this through a two-layer design:

1. **Yjs helper** (`src/appflowy_mcp_toolkit/collab/yjs_helper.js`): Node.js 18+ script
   that reads `{doc_state: [...], operation: "..."}` from stdin and writes the mutation
   result to stdout as JSON.  No network access, no tokens passed to Node.
2. **Python wrapper** (`collab/collab_delete.py`, `client.delete_database_row_collab()`):
   fetches binary collab, invokes the helper via subprocess, and (in live mode) POSTs
   the incremental delta.

**Safety gates for live mode (all required):**
- `dry_run=False` passed explicitly.
- `APPFLOWY_ALLOW_WRITES=true` in environment.
- `APPFLOWY_ALLOW_COLLAB_WRITES=true` in environment.
- Row must be present in binary collab (not just REST row list).

**Node.js dependency:** the `yjs` npm package (MIT) must be installed once:
`cd src/appflowy_mcp_toolkit/collab && npm install`.

**License:** `yjs` is MIT.  No AGPL code is used.  The `appflowy-collab` Rust library
(AGPL-3.0) is *not* a dependency.

**Status:** live-tested as part of the task data-plane lifecycle against disposable
self-hosted AppFlowy workspaces.  Current delete verification means the row
is removed from database view row lists and REST row lists; explicit row-detail lookup by
id may still return the old row object on some AppFlowy deployments. Browser Board
rendering is not treated as authoritative because of the known AppFlowy Web Board/Grid
refresh issue.

See `docs/rest-vs-collab.md` for the operational decision table. The important rule is:
use REST and `task_key` for agent-managed tasks; use collab-by-`row_id` only for
existing manual rows or for row deletion, where REST cannot target the desired object.

## pre_hash and MCP-managed task upserts

`pre_hash` is used exclusively for MCP-managed idempotent task upserts
(`upsert_managed_task`, `move_managed_task_status`). The caller supplies a stable
`task_key` string; the client passes it as `pre_hash` in the PUT body so the same logical
task can be created-or-updated without knowing the internal AppFlowy row ID.

This pattern is tested and works against the current AppFlowy Cloud API. The precise
server-side semantics of `pre_hash` (e.g. whether it is a true idempotency key or a
content hash) are not part of the public API documentation, so this toolkit deliberately
limits its use to this one controlled pattern rather than exposing it as a general feature.

## Task-facing API

The public task surface is intentionally narrower than the lower-level row/collab
diagnostics:

- `list_tasks` reads task row ids and row details from the database data plane.
- `create_task` creates an MCP-managed task using a stable `task_key`.
- `update_task` updates description/status/document fields for the same stable `task_key`.
- `move_task` is a status-only wrapper for common board movement.
- `update_database_row_by_id_collab` updates existing/manual rows by AppFlowy `row_id`.
- `move_task_by_row_id` is the status-only wrapper for existing/manual task rows.
- `delete_task` deletes by AppFlowy `row_id` through the experimental Yjs collab path.

For the current board shape, the required task fields are `Description` and `Status`.
The toolkit returns the AppFlowy row id from create/list so callers can later delete the
same row. Delete deliberately does not accept only `task_key`: AppFlowy does not expose
a confirmed lookup-by-`pre_hash` delete path, and a delete operation must never create or
upsert a missing task merely to discover its row id.

Verification is data-plane first: REST row list/detail, database `row_orders`, row collab,
and optionally blob/diff. Browser Board rendering is tracked separately because AppFlowy
Web can show stale Board cards until Grid/refresh warm-up.

## API namespace

The toolkit targets the `/api/workspace/...` endpoints documented in the public AppFlowy
OpenAPI spec.

`POST /api/v1/workspace/get_folder` was tested during early API mapping and returned
404; it is not implemented. Other `/api/v1/...` row and view endpoints
(row/create, row/update, row/delete, view/delete, view/update) are also not implemented:
they are absent from the official public OpenAPI and require official documentation plus
independent live verification before any implementation is attempted.
