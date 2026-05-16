# Roadmap

## M0 — local repo foundation

- [x] README, DESIGN, ROADMAP, coordination notes.
- [x] Package skeleton.
- [x] Generic env example.
- [x] Research reports.

## M1 — read-only client/services

- [x] Config/env loading.
- [x] HTTP client with bearer auth and optional refresh retry.
- [x] AppFlowy error normalization.
- [x] Workspaces, folder, databases, fields, rows, row details.
- [x] Offline tests with mocked HTTP.

## M2 — CLI inspection

- [x] CLI entrypoint.
- [x] JSON output for core read commands.
- [x] Manual smoke against real AppFlowy account.

## M3 — MCP read-only server

- [x] FastMCP entrypoint.
- [x] Read-only tools.
- [x] In-process MCP tests (tool registration + annotation + health check smoke).
- [x] Manual stdio MCP smoke: list tools + health.

## M4 — public cleanup

- [x] Secret scan.
- [x] Remove private paths/IDs.
- [x] Review docs for genericity.
- [x] Decide license (MIT).
- [ ] Create public GitHub repo.

## M5 — safe writes later

- [x] Explicit write-enable flag.
- [x] Dry-run create/upsert row.
- [x] Post-write verification in local disposable workspace smoke test.
- [x] Disposable write integration smoke test.
- [x] Manual stdio MCP write smoke in disposable workspace.

## M6 — AppFlowy Web collab driver

- [x] Verify real web delete behavior in a disposable workspace.
- [x] Add read-only collab JSON/row-order inspector.
- [x] Audit whether current REST writes are web-board visible.
- [x] Prototype AppFlowy-compatible collab mutation for task delete.
- [x] Integrate experimental Yjs row-delete into MCP/CLI/client (gated, dry-run default).
- [ ] Prove create/edit/move/delete against a disposable web board.
- [ ] Integrate verified task operations into MCP behind explicit experimental gates.

Current status: Yjs delete is integrated as an experimental tool (`appflowy_delete_database_row`)
behind two explicit env gates (`APPFLOWY_ALLOW_WRITES` + `APPFLOWY_ALLOW_COLLAB_WRITES`)
and a Node.js runtime requirement. Live-tested against a disposable workspace (M6.3).
Board create/edit/move equivalence is not yet proven (M6.4 pending).

Before adding more AppFlowy features, pause for stabilization: review the M6 diff,
align docs, keep dependencies explicit, and commit a coherent experimental baseline.

See [docs/collab-driver-plan.md](docs/collab-driver-plan.md).
Execution plan: [docs/execution-roadmap.md](docs/execution-roadmap.md).

### Deferred

- `/api/v1/workspace/get_folder`: live-tested against `beta.appflowy.cloud` and returned
  404. Not implemented.
- `/api/v1/` row/create, row/update, row/delete, view/delete, view/update: not
  implemented; absent from official public OpenAPI (which documents only the
  `/api/workspace/...` namespace). Require official documentation and independent
  live verification before any implementation is attempted.
- REST row delete and view delete operations: no confirmed public REST endpoint exists.
  Row delete is available only through the experimental Yjs collab tool above; view
  delete remains out of scope until a safe, verified pattern is established.
