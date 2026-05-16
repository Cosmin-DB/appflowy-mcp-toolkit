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
- AppFlowy Web at `appflowy.com/app/<workspace>/<board-view>` still rendered all
  board columns with count `0` after reload and after clearing the browser's AppFlowy
  IndexedDB caches.
- Follow-up `blob/diff` inspection confirmed the browser-facing binary endpoint returns
  row document seeds for the disposable database: 19 creates and 3 deletes. The deleted
  proof row appears as a delete operation in `blob/diff`, and the currently ordered rows
  appear as create operations with non-empty doc-state bytes.
- Despite that, the live browser IndexedDB cache still showed `rows = 0` and the board
  columns still rendered `0`. This narrows the gap: REST/collab row data and blob/diff
  row seeds exist, but AppFlowy Web is not applying/rendering them in this disposable
  workspace page. The next slice should inspect the web-side preload/apply failure or
  test against a browser-created page/database as a control.
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
- Therefore the current REST create path is **not proven web-board-visible**. More
  importantly, REST success plus database `row_orders` membership is insufficient
  evidence for a real AppFlowy Web board card.

Next investigation slice: map the exact web create transaction for a card and compare it
with the REST-created row shape. Do not promote REST create into a high-level
`appflowy_create_task` tool until MCP create can reproduce the web-visible local/live row
semantics or the limitation is explicitly accepted.

### M6.5 MCP Integration (partial — experimental gate only)

- [x] Wrap the Yjs prototype as a tracked helper with runtime checks and JSON output.
- [x] Add a second opt-in flag for experimental collab writes (`APPFLOWY_ALLOW_COLLAB_WRITES`).
- [x] Keep dry-run behavior (default).
- [x] Check binary collab presence before delete; surface `row_found=False` on lag.
- [x] Keep destructive tools explicit and narrow.
- [ ] Add task tools beyond delete only after M6.4 passes.
- [ ] Full board create/edit/move/delete loop, not just delete.

Current stabilization note: M6.5 is integrated but should be treated as a frozen
experimental baseline until reviewed and committed. Do not start new task operations
or broader collab mutations before M6.4 proves the full disposable board loop.

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
