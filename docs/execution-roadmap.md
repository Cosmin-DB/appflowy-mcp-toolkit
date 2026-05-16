# Execution Roadmap

This roadmap turns the current experimental AppFlowy MCP toolkit into a reliable
task-board MCP without depending on large, ambiguous work packets.

## Current baseline

The repo has advanced past the cleanup baseline. Latest committed checkpoint before the
current blob/diff work is `bf326c3` (`Record AppFlowy board create proof`).

Implemented:

- Read-only AppFlowy inspection through CLI and MCP.
- Guarded REST row creation/upsert/status operations.
- Read-only collab JSON and row-order inspection.
- Read-only blob/diff inspection for AppFlowy Web row-document seed diagnostics.
- Experimental Yjs row delete through client, CLI, and MCP.
- Safety gates for writes and collab writes.

Not yet proven:

- Full create/edit/move/delete equivalence with AppFlowy Web board behavior.
- Higher-level task automation semantics.
- Public release readiness.

## Development rule

The coordinator owns architecture, sequencing, integration, and final truthfulness.
Workers may be used only for small, bounded tasks with a narrow write set and a
clear verification gate.

Avoid assigning one worker combined research, implementation, live testing, docs,
and release cleanup.

## Phase 1 - M6.4 disposable board proof

Goal: prove what operations actually behave like normal AppFlowy Web board cards.

Each item is a separate task.

1. **Create proof**
   - Create one disposable task through the MCP/CLI path.
   - Verify it appears in AppFlowy Web Grid.
   - Verify whether it appears in Board without manual repair.
   - Record REST row data and collab row_orders evidence.
   - If the board does not render it, inspect the browser's blob/diff seed path
     before moving on to edit/move tooling.

2. **Edit proof**
   - Edit title/description/status fields on one disposable row.
   - Verify changes in AppFlowy Web.
   - Verify REST and collab state after refresh.

3. **Move/status proof**
   - Move one disposable task between status groups.
   - Verify the board column changes in AppFlowy Web.
   - Determine whether ordering inside a column is controlled by REST cell update,
     row_orders, or another collab field.

4. **Integrated delete proof**
   - Delete one disposable task using the tracked MCP/CLI Yjs path, not the old local
     prototype.
   - Verify absence in AppFlowy Web, collab row_orders, and REST row list.

Exit criteria:

- A short evidence note for each operation.
- `docs/collab-driver-plan.md` updated with exact findings.
- No production/private workspace mutations.

## Phase 2 - Define stable task semantics

Goal: decide what a "task" means for this MCP.

Outputs:

- Required task fields.
- Supported field types.
- Status/group movement semantics.
- Ordering support: supported, unsupported, or explicitly deferred.
- Difference between generic database rows and task-board cards.

Exit criteria:

- `DESIGN.md` has a stable task model section.
- README no longer implies more board support than verified.

## Phase 3 - Implement high-level task tools

Goal: expose user-facing task operations only after Phase 1 and Phase 2 are clear.

Candidate tools:

- `appflowy_create_task`
- `appflowy_update_task`
- `appflowy_move_task`
- `appflowy_delete_task`
- `appflowy_list_tasks`

Rules:

- Keep low-level row tools available but documented as lower-level primitives.
- Keep all mutations dry-run by default.
- Preserve write gates.
- Add post-write verification for each operation.

Exit criteria:

- Unit tests for each tool.
- Disposable live smoke tests for the full task lifecycle.
- MCP tool annotations reviewed.

## Phase 4 - Hardening and packaging

Goal: make the toolkit installable and less fragile.

Tasks:

- Decide how the Node/Yjs helper is installed and checked.
- Improve error messages for missing Node/npm dependency.
- Add a dedicated setup/check command if useful.
- Decide whether to keep Node/Yjs or later replace it with a Rust `yrs` helper.
- Verify package data includes the JS helper and package metadata.

Exit criteria:

- Fresh checkout setup documented.
- `appflowy-toolkit health` or equivalent catches missing runtime pieces.
- Tests cover missing-helper and missing-node paths.

## Phase 5 - Safety/release gate

Goal: prepare for public repo or serious local use.

Checks:

- Full test/lint/typecheck gates.
- Secret and private-ID scan over tracked files.
- Docs genericity review.
- License/dependency review.
- Confirm `.local`, caches, `.venv`, `node_modules`, and generated dumps are ignored.
- Confirm no real workspace IDs, tokens, emails, or captured realtime payloads are committed.

Exit criteria:

- Release checklist complete.
- Cosmin explicitly confirms publication or external use.

## Phase 6 - Publication / integration

Goal: publish or wire the MCP into regular use.

Tasks:

- Create public GitHub repo only after approval.
- Add installation instructions.
- Add MCP client configuration example.
- Add known limitations.
- Add a small manual smoke-test script.

Exit criteria:

- Fresh environment can install and run read-only tools.
- Experimental writes remain opt-in.
- Task-board lifecycle is either proven or clearly marked as limited.

## Immediate next step

Start Phase 1, item 1 only: create proof for one disposable task. Do not start edit,
move, delete, packaging, or publication until that evidence is written down.
