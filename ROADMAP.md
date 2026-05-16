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

## M5 — guarded writes

- [x] Explicit write-enable flag.
- [x] Dry-run create/upsert row.
- [x] Post-write verification in local disposable workspace smoke test.
- [x] Disposable write integration smoke test.
- [x] Manual stdio MCP write smoke in disposable workspace.

## M6 — AppFlowy Web collab driver and task data plane

- [x] Verify real web delete behavior in a disposable workspace.
- [x] Add read-only collab JSON/row-order inspector.
- [x] Audit whether current REST writes are web-board visible.
- [x] Prototype AppFlowy-compatible collab mutation for task delete.
- [x] Integrate experimental Yjs row-delete into MCP/CLI/client (gated, dry-run default).
- [x] Prove create/edit/move/delete at the AppFlowy data plane against a disposable
  official workspace.
- [x] Integrate verified task operations into MCP behind explicit write gates.
- [x] Add opt-in browser smoke against local AppFlowy Web.
- [ ] Prove direct Browser Board rendering for MCP-created rows without AppFlowy Web
  rendering/cache limitations.

Current status: task-facing tools (`appflowy_list_tasks`, `appflowy_create_task`,
`appflowy_update_task`, `appflowy_move_task`, `appflowy_delete_task`) are integrated.
They are dry-run by default and require explicit write gates for mutation. Yjs delete is
integrated as an experimental path behind `APPFLOWY_ALLOW_WRITES` +
`APPFLOWY_ALLOW_COLLAB_WRITES` and a Node.js runtime requirement. Official live smoke
covers the create/update/move/delete data-plane lifecycle. Browser Board rendering remains
a separate AppFlowy Web cache/rendering concern.

See [docs/collab-driver-plan.md](docs/collab-driver-plan.md).
Execution plan: [docs/execution-roadmap.md](docs/execution-roadmap.md).
Full AppFlowy coverage matrix: [docs/appflowy-coverage-matrix.md](docs/appflowy-coverage-matrix.md).

## Self-hosted AppFlowy Docker tests

The pre-Docker MCP-side checklist is complete:

- [x] Freeze `task_key`/`pre_hash` as the public managed-task identity.
- [x] Add final task-facing tool names (`create_task`, `update_task`, `move_task`,
  `delete_task`, `list_tasks`) as safe wrappers around the verified managed-task/data-plane
  implementation.
- [x] Keep low-level row/collab tools as diagnostics, not the main public workflow.
- [x] Add one browser/UI acceptance skeleton for Grid/Board rendering, documenting the
  known AppFlowy Web Board refresh/cache bug separately from data-plane correctness.
- [x] Align README, DESIGN, ROADMAP and collab-driver docs with the verified live smoke.
- [x] Re-run unit gates and the official opt-in live smoke.

The Docker/self-hosted phase now exists and has been validated:

- [x] Optional compose workflow under `docker/appflowy-test/` using the official
  `AppFlowy-IO/AppFlowy-Cloud` source at a pinned tag/commit.
- [x] Start/teardown scripts for a disposable local stack.
- [x] Seed script that signs up or reuses a local test user, verifies it through GoTrue,
  discovers a workspace/database, and emits `.env.selfhosted.generated`.
- [x] Opt-in destructive self-hosted task lifecycle test under `tests/selfhosted/`.
- [x] Full local validation: stack health, web redirect, seed reuse, self-hosted
  lifecycle, offline suite, lint, format, typecheck, and official live smoke.

Remaining Docker/UI work: full visual parity. The opt-in browser smoke can log in and
render Grid, but MCP-created rows are currently verified at the REST/collab/blob-diff
data plane and recorded as `xfail` when this AppFlowy Web build does not render them.

Detailed Docker/self-hosted testing plan: [docs/self-hosted-test-plan.md](docs/self-hosted-test-plan.md).

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
