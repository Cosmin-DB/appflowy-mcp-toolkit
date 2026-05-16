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
Row delete is available only through the experimental Yjs collab path (see below).
No view/page delete, bulk operations, or workspace admin tools are included.

## Collab diagnostics

The toolkit includes read-only collab inspection helpers for database documents:

- `get_collab_json` fetches the JSON representation of a collab object through
  `/api/workspace/v1/{workspace_id}/collab/{object_id}/json`.
- `get_database_row_orders` extracts per-view `row_orders` from the database collab.

These diagnostics exist because AppFlowy Web board operations are backed by Yjs/AppFlowy
collab state. They are intentionally read-only and do not perform binary collab writes.

## Experimental: Yjs-based row delete (M6.3)

AppFlowy Web does not expose a REST row-delete endpoint. Deletion is a Yjs collab
mutation: the row ID is removed from every view's `row_orders` YArray in one transaction,
and the incremental lib0-v1 update is posted to
`/api/workspace/v1/{workspace_id}/collab/{database_id}/web-update`.

The toolkit implements this through a two-layer design:

1. **Yjs helper** (`src/appflowy_mcp_toolkit/collab/yjs_helper.js`): Node.js 18+ script
   that reads `{doc_state: [...], row_id: "..."}` from stdin and writes the mutation
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

**Status:** live-tested against a disposable workspace (M6.3).  Not yet proven for
all board create/edit/move scenarios.  Not recommended for production until M6.4
(end-to-end verification) passes.  Current delete verification means the row is
removed from database view row lists; explicit row-detail lookup by id may still
return the old row object.

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
