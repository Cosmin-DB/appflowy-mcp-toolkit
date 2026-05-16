# Execution Roadmap

This roadmap turns the current experimental AppFlowy MCP toolkit into a reliable
task-board MCP without depending on large, ambiguous work packets.

## Current baseline

The repo is now a pre-1.0 release candidate with a self-contained Docker-based
validation workflow.

Implemented:

- Read-only AppFlowy inspection through CLI and MCP.
- Guarded REST row creation/upsert/status operations.
- Read-only collab JSON and row-order inspection.
- Read-only blob/diff inspection for AppFlowy Web row-document seed diagnostics.
- Data-plane row verification through REST row list/detail, database `row_orders`,
  DatabaseRow collab JSON, and optional blob/diff diagnostics.
- Verified create path exposed through CLI/client/MCP for controlled task-row proof.
- Task-facing CLI/MCP tools for list/create/update/move/delete.
- Opt-in self-hosted acceptance tests for the managed task lifecycle data plane
  against a disposable local AppFlowy database.
- Experimental Yjs row delete through client, CLI, and MCP.
- Safety gates for writes and collab writes.
- Optional self-hosted Docker test workflow using pinned AppFlowy-Cloud/AppFlowy Web
  images, deterministic env overrides, seed/auth script, and destructive local lifecycle
  tests.

Not yet proven:

- Direct board-load behavior for created rows without a Grid warm-up.
- Full browser-rendered edit/move/delete equivalence with AppFlowy Web board behavior.
- Full AppFlowy Web visual parity for MCP-created rows. The current browser smoke records
  this as xfail when the data plane verifies but AppFlowy Web does not render the row.

## Development rule

The coordinator owns architecture, sequencing, integration, and final truthfulness.
Workers may be used only for small, bounded tasks with a narrow write set and a
clear verification gate.

Avoid assigning one worker combined research, implementation, live testing, docs,
and release cleanup.

## Phase 1 - M6.4 disposable board/data-plane proof

Goal: prove task operations at the AppFlowy data plane and document where AppFlowy Web
Board rendering diverges.

Each item is a separate task.

1. **Create proof** — done at data plane; UI behavior documented
   - Create one disposable task through the MCP/CLI path.
   - Verify it appears in AppFlowy Web Grid.
   - Verify whether it appears in Board directly and after Grid warm-up.
   - Record REST row data and collab row_orders evidence.
   - If the board does not render it, inspect the browser's blob/diff seed path
     before moving on to edit/move tooling.

2. **Edit/update proof** — done at data plane through managed task update
   - Edit title/description/status fields on one disposable row.
   - Verify changes in AppFlowy Web.
   - Verify REST and collab state after refresh.

3. **Move/status proof** — done at data plane through managed task move
   - Move one disposable task between status groups.
   - Verify the board column changes in AppFlowy Web.
   - Determine whether ordering inside a column is controlled by REST cell update,
     row_orders, or another collab field.

4. **Integrated delete proof** — done at data plane through tracked Yjs path
   - Delete one disposable task using the tracked MCP/CLI Yjs path, not the old local
     prototype.
   - Verify absence in AppFlowy Web, collab row_orders, and REST row list.

Exit criteria status:

- Data-plane lifecycle evidence is recorded in `docs/collab-driver-plan.md`.
- Browser UI rendering is explicitly split into `docs/browser-ui-acceptance.md`.
- No production/private workspace mutations are required for the tests.

## Phase 2 - Define stable task semantics — done

Goal: decide what a "task" means for this MCP.

Outputs:

- Required task fields.
- Supported field types.
- Status/group movement semantics.
- Ordering support: supported, unsupported, or explicitly deferred.
- Difference between generic database rows and task-board cards.

Status: `task_key` maps to AppFlowy `pre_hash` for create/update/move. Delete uses
the returned/listed AppFlowy `row_id` because there is no safe confirmed lookup-by-key
delete path. Ordering inside a Board column remains deferred.

## Phase 3 - Implement high-level task tools — done

Implemented tools:

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
- Disposable self-hosted smoke tests for the full task lifecycle.
- MCP tool annotations reviewed.

## Phase 4 - Hardening and packaging — partial

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

Next small slice: run the pre-release battery, package/build verification, and
secret/private-ID scan from a clean checkout. Browser/UI acceptance remains a separate
quality layer because the current OpenClaw browser policy blocks direct localhost
navigation; local Chrome headless can render the AppFlowy web shell, but it is not a
full login/UI lifecycle pass. Do not publish until UI limitations, setup requirements,
and release safety are reviewed.

## Pre-Docker MCP Checklist — complete

These MCP-side items were completed before the local AppFlowy Docker rig was added.
They are historical planning notes; the current contributor workflow is Docker-first.

1. **Freeze the task-board contract** — done
   - Decide the public task identity: `task_key` as the MCP-owned stable id.
   - Define required fields: `Description` and `Status` for the current board shape.
   - Document that `task_key` maps to AppFlowy `pre_hash` and returns/keeps a row id.

2. **Expose final task tools, still behind safety gates** — done
   - Add thin public aliases/wrappers for:
     - `appflowy_create_task`
     - `appflowy_update_task`
     - `appflowy_move_task`
     - `appflowy_delete_task`
     - `appflowy_list_tasks`
   - Keep lower-level row/collab tools available as diagnostics.
   - Keep dry-run defaults and write/collab gates.

3. **Complete one disposable task lifecycle evidence note** — done
   - Record create/update/move/delete data-plane results from disposable smoke.
   - Record AppFlowy Web rendering separately from data-plane verification.
   - Explicitly mark Board/Grid rendering gaps as UI behavior unless data-plane checks fail.

4. **Add browser/UI acceptance skeleton** — done
   - Add a documented manual or opt-in browser check for Grid/Board rendering.
   - Do not block task data-plane correctness on AppFlowy Web Board cache behavior.

5. **Clean release-facing docs** — done
   - README says what is stable, experimental, and known-limited.
   - DESIGN documents the task model and verification model.
   - ROADMAP no longer says M6.4 is pending if the data-plane lifecycle is already
    covered by self-hosted tests.

6. **Run the current gates before starting Docker work** — done
   - `uv run ruff format .`
   - `uv run ruff check .`
   - `uv run mypy src`
   - `uv run pytest -q`
   - Opt-in self-hosted smoke with disposable local ids.

This checklist was completed before the self-hosted rig was added.

Detailed plan: `docs/self-hosted-test-plan.md`.

## Self-Hosted Docker Testing — implemented and validated

Current workflow:

- `docker/appflowy-test/` contains the optional test stack config and docs.
- `scripts/appflowy_test_env_up.sh` fetches the pinned official AppFlowy-Cloud source
  and starts the local stack.
- `scripts/appflowy_test_seed.py` signs up or reuses the local test user, verifies the
  account, discovers a task-compatible database, and writes `.env.selfhosted.generated`.
- `tests/selfhosted/` contains the opt-in destructive task lifecycle coverage for the
  local disposable stack.

Validated status from the latest full battery:

- Docker stack health OK and AppFlowy Web redirects to `/app`.
- Seed reuse is idempotent for the one-seat local license behavior.
- Self-hosted integration tests: 9 passed.
- Browser smoke: 2 passed in the latest run; the row-rendering test may still record
  an expected xfail on stale AppFlowy Web rendering builds.
- Offline unit pytest: 117 passed.
- Ruff format/check, mypy, build, and diff check passed.

Remaining work:

- Full visual parity for MCP-created rows in AppFlowy Web.
- Secret/private-ID scan before publication.
- Public GitHub repo only after Cosmin confirms.
