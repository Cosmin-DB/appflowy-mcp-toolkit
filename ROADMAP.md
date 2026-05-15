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

### Deferred

- `/api/v1/workspace/get_folder`: live-tested against `beta.appflowy.cloud` and returned
  404. Not implemented.
- `/api/v1/` row/create, row/update, row/delete, view/delete, view/update: not
  implemented; absent from official public OpenAPI (which documents only the
  `/api/workspace/...` namespace). Require official documentation and independent
  live verification before any implementation is attempted.
- Row delete and view delete operations: no confirmed public REST endpoint exists;
  out of scope until a safe, reversible pattern is established.
