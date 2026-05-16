# AppFlowy Collab Driver Plan

## Why this phase exists

The public AppFlowy REST row endpoints are not enough for a complete task-board MCP.
Live browser testing showed that AppFlowy Web deletes a board card by mutating the
database collaboration document, not by calling a semantic row-delete REST endpoint.

The toolkit should therefore treat REST row writes as limited/experimental until we
prove that the operation is visible and consistent in AppFlowy Web.

## Target outcome

Provide MCP tools that can create, edit, move, and delete tasks as AppFlowy Web board
cards, with the same visible result a user gets from the browser UI.

## Non-goals

- Do not invent undocumented `/api/v1/.../delete` endpoints.
- Do not delete row collab objects directly with `DELETE /collab/{row_id}`.
- Do not publish destructive tools before disposable-workspace verification.
- Do not commit private workspace IDs, tokens, or captured network payloads.

## Working model

AppFlowy Web stores database state in a Yjs/AppFlowy-Collab document. Task-board
operations update that document, then sync a binary update to AppFlowy Cloud through
the realtime channel or the generic `web-update` endpoint.

For task deletion, the confirmed web behavior is:

1. Find the row id in each database view's `row_orders`.
2. Remove that row id from every `row_orders` array.
3. Clear local row outbox/collab cache for the row.
4. Sync the database collab update.

The MCP implementation should reproduce the semantic collab operation, not approximate
it through JSON string manipulation or unrelated delete endpoints.

## Milestones

### M6.0 Evidence Pack

- [x] Verify the real web delete button in a disposable workspace.
- [x] Confirm no semantic REST row-delete request is emitted by the browser.
- [x] Confirm AppFlowy Cloud REST row route exposes GET/POST/PUT, not DELETE.
- [x] Record that current REST writes are not yet proven equivalent to web board cards.

### M6.1 Read-only Collab Inspector

- [x] Add client support for `GET /api/workspace/v1/{workspace_id}/collab/{object_id}/json`.
- [x] Add a safe helper that extracts database view ids and `row_orders`.
- [x] Expose this through CLI/MCP as read-only diagnostics.
- [x] Add offline tests with fixture responses.
- [x] Live read-only smoke against the disposable workspace.

### M6.2 Current Write Audit

- [x] Re-check existing REST create/upsert/move behavior against web-visible board state.
- [x] Decide whether existing task write tools should be renamed, hidden, or marked legacy.
- [x] Update README, DESIGN, and safety docs with the result.

Current decision: keep the existing REST write tools, but document their exact scope.
They correctly create/update database rows, appear in collab `row_orders`, and render in
AppFlowy Web Grid after refresh/navigation; some board cards render too, but full board
card behavior and ordering are not yet proven. They update task status cells, but they do
not control intra-column card ordering. Full task automation still needs a collab/Yjs
driver for delete and positional moves.

### M6.3 Collab Mutator Prototype

- [x] Build an experimental local helper that uses AppFlowy-compatible Yjs logic.
- [x] Start with delete because the web behavior is now known and compact.
- [x] Produce a binary update for `web-update`; do not hand-edit JSON.
- [x] Require an explicit disposable workspace/database allowlist for live mutation tests.

Prototype result: a local Node.js helper using the MIT-licensed `yjs` package fetched the
binary database collab document, removed a row id from every view's `row_orders`, produced
an incremental lib0-v1 update, and posted it to `web-update`. Live disposable-row deletes
were verified through binary collab and REST row-list reads. Important nuance: explicit
row-detail lookup by id may still return the row object after it has been removed from all
view `row_orders`; current delete semantics are therefore remove from database views/cards,
not guaranteed physical row-collab purge. The prototype lives under
`.local/prototypes/yrs-delete-mutator/`.

Integration result: the prototype was wrapped as a tracked helper under
`src/appflowy_mcp_toolkit/collab/` for experimental MCP/CLI/client use. The public toolkit
remains MIT-only by depending on `yjs`, not AGPL `appflowy-collab`. A future Rust `yrs`
helper is still possible, but it is not required for the current experimental baseline.

### M6.4 End-to-End Disposable Workspace Proof

- [x] Create a task through the current REST/MCP path and inspect REST/collab state.
- [ ] Create a task that appears in AppFlowy Web.
- [ ] Move it between board groups.
- [ ] Edit its title/description/status.
- [x] Delete a disposable row through the local Yjs prototype.
- [ ] Verify after each step through AppFlowy Web and collab/REST reads.

Create proof result, 2026-05-16:

- Live target was the disposable `MCP Toolkit Test 2026-05-15 15:36 UTC` workspace.
- `appflowy-toolkit create-row --execute` returned a successful row id.
- REST row detail immediately contained:
  - `Description = MCP M6.4 CREATE PROOF 20260516T072707Z`
  - `Status = To Do`
  - `has_doc = true`
- Database collab JSON included the new row id at the end of all three observed
  `row_orders` arrays: inline grid, named `Grid`, and board view.
- The new row's `DatabaseRow` collab contained field-id keyed cells:
  `phVRgL` for `Description`, `SqwRg1` with option id `CEZD` for `To Do`.
- Initial AppFlowy Web board checks at `appflowy.com/app/<workspace>/<board-view>`
  rendered all board columns with count `0` after reload and after clearing the
  browser's AppFlowy IndexedDB caches. This was later found to be an incomplete
  verification because the Grid view had not been loaded first.
- Follow-up `blob/diff` inspection confirmed the browser-facing binary endpoint returns
  row document seeds for the disposable database: 19 creates and 3 deletes. The deleted
  proof row appears as a delete operation in `blob/diff`, and the currently ordered rows
  appear as create operations with non-empty doc-state bytes.
- Follow-up manual control from Cosmin (`test_ela_manual`) showed the missing piece:
  the row existed in REST row list, all three `row_orders`, and DatabaseRow collab
  (`Description = test_ela_manual`, `Status = To Do`). It did not show in the board-only
  view at first, but after opening the `Grid` tab it rendered correctly in Grid; returning
  to the board then showed populated columns and the card in `To Do`. This means the
  earlier conclusion "REST-created rows do not appear in AppFlowy Web" was too strong.
  The more precise limitation is a board preload/rendering path: direct board load may
  initially show 0 until row documents are loaded through Grid/blob seeds.
- Browser-created control: pressing Enter in the web board's new-card input created an
  `Untitled` card that immediately appeared in the `To Do` board column. The new row id
  was inserted at the front of all three `row_orders` arrays and appeared in the REST row
  id list, but `row/detail` returned an empty list and `blob/diff` changed to `PENDING`
  with `database blob diff awaiting 1 live row`. This proves the web create path has a
  live/local row state that is not equivalent to the existing REST create response.
- The browser-created control row was cleaned up through the integrated `delete-row
  --execute` path. It disappeared from AppFlowy Web, all three `row_orders`, and the REST
  row id list; explicit row-detail lookup was also absent for this specific row.
- Cleaning up that proof row through the integrated `delete-row --execute` path removed it
  from all three view `row_orders` and from the REST row-list endpoint. Explicit
  `row/detail?ids=<row_id>` still returned the row object, so the implementation now reports
  row-list verification separately from row-detail resolvability.
- Therefore the current REST create path is **partially proven web-visible**: rows can
  appear in AppFlowy Web Grid and then Board after row-document preload. What remains
  unproven is reliable direct board rendering without requiring a manual Grid warm-up,
  plus the full edit/move/delete lifecycle.
- Follow-up implementation added a data-plane verification layer:
  `verify-row` / `appflowy_verify_database_row` checks REST row list, REST row detail,
  database `row_orders`, DatabaseRow collab JSON, and optional `blob/diff`.
  `create-verified-row` / `appflowy_create_verified_database_row` creates a row and
  immediately runs that verification. A live disposable-row proof against AppFlowy
  official created row `00f6c6ef-00a2-4d3a-9f68-3cb34d16e592` with
  `Description = ela_verified_create_1778920907`; verification found it in REST row
  list, REST detail, all three observed `row_orders`, and DatabaseRow collab.
  The same row did not immediately render in the browser snapshot, reinforcing that
  UI visibility must be tested separately from data-plane correctness.
- Managed task live proof: `upsert_managed_task` with a stable `task_key` created row
  `9c4d741a-7f4f-c2f1-292d-dcfc9d28bd37`, and `move_managed_task_status` with the
  same key moved it to `Status = Doing` while preserving the row id. Data-plane
  verification found the moved row in REST row list/detail, all three observed
  `row_orders`, and DatabaseRow collab. This supports using `task_key`/`pre_hash` as
  the stable MCP-owned task identity for create/edit/move operations.
- Added opt-in live acceptance test `tests/live/test_task_lifecycle.py`. It requires
  `APPFLOWY_LIVE_TESTS=true`, disposable workspace/database ids, and both write gates.
  The live official AppFlowy run passed on 2026-05-16: create managed task, move to
  `Doing`, delete via Yjs collab, verify collab absence and REST row-list absence.
  This is now the first platform-level data-plane smoke test; AppFlowy Web UI/Board
  rendering still remains a separate browser acceptance layer because of the known
  Board/Grid cache issue.
- Cosmin independently reproduced the Board/Grid bug in his own AppFlowy official
  workspace on Firefox and Chrome: refreshing/F5 on Board makes cards disappear, then
  opening Grid and returning to Board makes them reappear. Treat this as an AppFlowy
  Web Board cache/preload/rendering issue and not an MCP data-write failure unless a
  future data-plane check contradicts it.

Task-facing create/update/move/delete tools now use the verified data-plane path. Browser
Grid/Board rendering is intentionally not used as the source of truth because the AppFlowy
Web Board can be stale until Grid/refresh warm-up.

Before starting a self-hosted AppFlowy Docker test rig, finish the MCP-side task-board
surface so the Docker work validates a coherent contract instead of a moving target:

- [x] Promote the verified managed-task operations into final task-facing tool names.
- [x] Keep diagnostic row/collab tools separate from the main public workflow.
- [x] Document the task model: `task_key`, row id, required fields, status movement, and
  ordering limitations.
- [x] Add/update one official live-smoke evidence note for data-plane lifecycle.
- [x] Add a browser/UI acceptance skeleton that records Grid/Board behavior separately from
  data-plane correctness.
- [x] Re-run unit/type/lint gates and the official opt-in live smoke.

Only after that should the project add `docker/appflowy-test/` or `tests/docker/` for
self-hosted destructive tests.

### M6.5 MCP Integration (partial — experimental gate only)

- [x] Wrap the Yjs prototype as a tracked helper with runtime checks and JSON output.
- [x] Add a second opt-in flag for experimental collab writes (`APPFLOWY_ALLOW_COLLAB_WRITES`).
- [x] Keep dry-run behavior (default).
- [x] Check binary collab presence before delete; surface `row_found=False` on lag.
- [x] Keep destructive tools explicit and narrow.
- [x] Add task tools beyond delete only after M6.4 passes.
- [x] Full data-plane create/edit/move/delete loop, not just delete.

Current stabilization note: M6.5 is integrated as an experimental baseline. Do not add
broader collab mutations until the self-hosted rig can run destructive tests repeatedly.

### M6.5.1 Stabilization Checkpoint

- [ ] Review the M6 diff as one architectural change.
- [ ] Ensure README, DESIGN, ROADMAP, safety docs, and this plan describe the same state.
- [ ] Decide whether `uv.lock` is ignored or tracked; default for this library is ignored.
- [ ] Keep `node_modules/` out of git while keeping `package.json` and `package-lock.json`.
- [ ] Run pytest, ruff format/check, mypy, and git diff check.
- [ ] Commit the coherent experimental delete baseline before launching more workers.

### M6.6 Publication Gate

- [ ] Full test/lint/typecheck gates.
- [ ] Secret/private-ID scan.
- [ ] Docs clearly separate REST diagnostics from web-board task automation.
- [ ] Public repo creation only after Cosmin confirms.

## Agent Workstreams

- Source/protocol agent: map AppFlowy Web, Cloud, and Collab source for the exact
  create/edit/move/delete paths.
- Read-only inspector agent: implement M6.1 in the Python toolkit.
- Write-audit agent: verify current REST writes and document whether they match web board
  semantics.
- Mutator-design agent: propose the smallest safe Rust/Node/Python helper strategy for
  M6.3 without committing to a broad rewrite.

## Development Mode After M6.5

The next phase should use small slices. The coordinator owns architecture, sequencing,
and integration. Workers, if used, should receive one narrow task with a clear write
scope and a fast verification gate.

Good next slices:

1. Verify web-visible create for one disposable card.
2. Verify edit semantics for one field set.
3. Verify move/status semantics and what ordering is or is not controlled.
4. Re-run delete through the integrated MCP/CLI path.
5. Only then design higher-level task tools.

Avoid combining source research, live experiments, implementation, docs, and release
cleanup in one worker brief.

## Safety Gates

- All live mutation tests must target a disposable workspace only.
- Destructive tests must create their own disposable row/card first.
- Every write path must have dry-run output and post-write verification.
- Tool output and docs must redact tokens, emails, real workspace IDs, and captured
  realtime URLs.
- Main coordination/review stays separate from implementation workers.
