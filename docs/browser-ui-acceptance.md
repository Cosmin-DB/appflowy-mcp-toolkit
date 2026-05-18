# Browser/UI Acceptance Skeleton

The MCP verifies task correctness through AppFlowy's API/collab data plane. Browser checks
are still useful, but they must not be mixed with data-plane truth because AppFlowy Web
Board rendering can be stale after refresh.

Use this checklist for manual or future automated browser acceptance against a disposable
workspace/database:

1. Create a task through `appflowy_create_task` or `appflowy-toolkit create-task --execute`.
2. Verify the returned `row_id` with `appflowy_verify_database_row`.
3. Open the Grid view and confirm the row exists with the expected `Description` and
   `Status`.
4. Open the Board view and record whether the card appears immediately.
5. Refresh the Board page and record whether cards disappear.
6. If cards disappear, open Grid, then return to Board and record whether cards reappear.
7. Move the task through `appflowy_move_task`; verify data plane first, then repeat Grid
   and Board observations.
8. Reorder a card through `appflowy_reorder_database_row`; verify the
   `row_orders` data plane first, then check Board/Grid rendering.
9. Reorder a board/status column through `appflowy_reorder_database_column`;
   verify the Database collab data plane first, then check Board rendering.
10. Delete the task through `appflowy_delete_task --execute` using the returned `row_id`;
   verify absence from row orders and REST row list.

Expected current behavior:

- Data-plane create/update/move/delete/reorder should pass.
- Board may hide cards after refresh until Grid is opened and Board is revisited. Treat
  that as a browser/UI finding, not an MCP mutation failure, unless REST/collab verification
  also fails.

Future automation can wrap this checklist with Playwright/OpenClaw browser control, but it
should keep two result channels: `data_plane` and `browser_rendering`.

## Browser-Gated Operation Matrix

Any command that promises a user-visible AppFlowy change must have browser acceptance
coverage before it is treated as release-safe. REST/collab/blob-diff checks prove the
data plane; they do not prove that AppFlowy Web reconstructs and renders the change.

| Operation family | Required browser assertion | Current gate |
|---|---|---|
| Create task/card through `create-task` / `appflowy_create_task` | New `Description` and `Status` are visible in Grid after creation; Board is recorded separately | implemented in `tests/browser/test_appflowy_web_smoke.py` |
| Refresh after create/edit | After page reload, the created/edited row still appears in Grid | required for future expansion |
| Update `Description` | Grid shows the new text and no longer shows the stale text for that row | required before claiming UI-safe update coverage |
| Move/update `Status` | Grid shows the new status; Board places the card in the expected column after Grid warm-up | required before claiming UI-safe move coverage |
| Delete task/card | Row disappears from Grid and Board, not only from REST row list or row_orders | required before claiming UI-safe delete coverage |
| Create/rename/hide/show board columns | Board shows the new/renamed/hidden/visible column state after refresh | implemented in `tests/browser/test_appflowy_web_board_acceptance.py` |
| Reorder rows/cards | Board or Grid visual order matches row_orders for the tested view/column | required for ordering release safety |
| Reorder board columns | Database collab group order changes; Board shows the involved columns after warm-up. Exact visual position remains a gap. | data-plane order + browser presence implemented in `tests/browser/test_appflowy_web_board_acceptance.py` |
| Typed row cells | Important field types render in Grid with expected human-readable values: select, multiselect, checkbox, date/time, checklist, media/link | required before broad typed-field UI claims |
| Page/view creation or movement | Sidebar/navigation shows the page/view in the expected place and opens without blank/error UI | required for page/view release safety |
| Append Markdown to page | AppFlowy Web page body shows the appended heading, paragraph, list item, and quote text | implemented in `tests/browser/test_appflowy_web_page_features.py` |
| Publish page | Public published URL shows the expected page title/content after publish | implemented in `tests/browser/test_appflowy_web_page_features.py` |
| Instantiate published page/template | Duplicated page opens in AppFlowy Web and shows expected source content | implemented in `tests/browser/test_appflowy_web_page_features.py` |
| Filters, sorts, layout, field settings | The view opens, applies the expected state, and survives refresh | required before enabling write tools for these view settings |
| Negative/path-regression case | A known unsafe or advanced path, such as fresh `pre_hash` upsert, fails the browser test if it does not render in Grid | required as a regression guard |

The default rule is conservative: if a human will judge the operation in AppFlowy Web,
the test must open AppFlowy Web and assert visible text/state. `curl` and REST checks
remain necessary, but they are not sufficient for user-visible workflows.

## 2026-05-18 AppFlowy Cloud Human Check

Cosmin and the OpenClaw browser both confirmed the following against AppFlowy Cloud:

- `create-task` produced a visible card in the real `To-dos` Board under `To Do`:
  `MCP human test 20260518T174900Z - tarea visible creada por Ela`.
- `create-page` plus `append-page-markdown` produced a visible page under `General`:
  `MCP human test page 20260518T174900Z`, with heading, paragraph, bullet items,
  accented text, number text, and quote block visible in the web page body.

This is human acceptance evidence for those two cloud workflows. It does not validate
publish/unpublish on AppFlowy Cloud, destructive cleanup, exact row/card ordering, or
all page/view movement paths.

Follow-up in the same human session also validated:

- task update/move: the test task title changed and moved from `To Do` to `Doing`;
- publish page: the published URL opened in an incognito/public browser and showed the
  expected page content;
- duplicate/instantiate published page: the published page was duplicated back into the
  workspace and opened with the expected copied content;
- unpublish page: the same public URL changed to AppFlowy's no-access/unpublished page;
- cleanup: the test task search returned no matches, and both test pages opened as
  `Page Deleted` after being sent to trash.

Remaining gaps after this cloud human pass: exact visual row/card/column ordering,
Quick Notes UI behavior, admin/member/invite flows, import/export, AI/chat routes, and
full block-level document editing.

## 2026-05-18 AppFlowy Cloud MCP-Only Smoke

After the human pass, a small MCP-only cloud smoke checked non-visual behavior:

- write gate: a live write without `APPFLOWY_ALLOW_WRITES=true` failed before network
  with the expected `Writes are disabled` error;
- local file upload gate: upload without `APPFLOWY_ALLOW_LOCAL_FILE_READS=true` failed
  before reading file contents;
- file v1 flow: uploaded `.env.example` under the To-dos database parent dir, read
  metadata, downloaded it byte-for-byte, then deleted it; post-delete metadata returned
  AppFlowy's expected not-found response;
- test pages: restore/trash/delete-trash routes returned success for both disposable
  pages used in the human acceptance pass;
- Quick Notes: create/update/delete returned success for a disposable note id, but
  `quick-notes` list remained empty before/after, so Quick Notes should not be called
  end-user-ready until its product/list behavior is understood.

## 2026-05-16 Local Browser Smoke

Current local evidence:

- The self-hosted AppFlowy Web container serves the app shell at `http://localhost/app`.
- A local headless Chrome smoke succeeded:

  ```bash
  google-chrome-stable --headless --no-sandbox --disable-gpu \
    --window-size=1365,768 \
    --screenshot=.local/browser-smoke/appflowy-local-app.png \
    http://localhost/app
  ```

- The screenshot file was produced at `.local/browser-smoke/appflowy-local-app.png` with
  size `1365x768`, proving the web app is reachable/renderable in the local Docker stack.
- OpenClaw's browser tool blocked direct navigation to `localhost`/`127.0.0.1` in this
  environment, so this is not yet a full CDP-driven login/UI lifecycle test.

Next browser-quality step: run Playwright or an allowed browser profile against the local
stack, sign into the seeded user, and execute the checklist above. Keep that as a
separate browser acceptance layer; the automated self-hosted pytest suite already proves
API/collab data-plane behavior.

## Playwright Smoke

The repo includes opt-in browser smoke coverage in `tests/browser/`:

```bash
set -a
source .env.selfhosted.generated
set +a
APPFLOWY_BROWSER_TESTS=true uv run --extra browser pytest tests/browser -q -s
```

Current expectations:

- Login and Grid rendering against the local Docker stack should pass.
- MCP-created rows are verified through REST/collab/blob-diff before the browser check.
- AppFlowy Web must render an MCP-created row in Grid. Board may still be stale
  after direct load, so Board screenshots remain diagnostic evidence, but missing
  Grid text is a failing browser/UI regression.
- Page feature tests must show appended Markdown text, published public-page content,
  and instantiated published-page content in the browser.

Validated 2026-05-16 against the local Docker stack: login + To-dos Grid rendering
passes. The row-rendering test first proves the MCP-created row at the data plane,
then checks AppFlowy Web Grid. Missing Grid rendering fails the test instead of being
hidden behind a data-plane-only pass.

## Board Acceptance Coverage (added 2026-05-18)

`tests/browser/test_appflowy_web_board_acceptance.py` adds three opt-in tests:

| Test | Assertion |
|---|---|
| `test_board_shows_created_task_after_grid_warmup` | Row description visible in Board body text after Grid warm-up |
| `test_board_reflects_status_move_after_grid_warmup` | Row + new status column both visible on Board after collab move |
| `test_board_row_reorder_data_plane_and_grid_presence` | Data-plane row order confirmed; both rows present in Grid |
| `test_board_status_option_lifecycle_visible_in_browser` | Stable MCP-owned Status option is visible after create/ensure, renamed visibly, hidden from Board, then shown again |
| `test_board_column_reorder_data_plane_and_browser_presence` | Board column order is confirmed through Database collab groups; involved columns are visible on Board |

### Board tab label

The Board tab label is resolved at runtime via `list_databases` (e.g. `"To-dos"`
in the self-hosted fixture, not a literal `"Board"` string).  Tests are therefore
independent of the human-readable view name.

### Board warm-up pattern

AppFlowy Web Board renders stale/empty state on direct navigation for freshly
created rows.  The established pattern — navigate → click Grid tab → click Board
tab — is required before Board card assertions are reliable.

### Gap: Board visual row ordering

Row reorder (`reorder_database_row_collab`) is confirmed at the data-plane via
`get_database_row_orders`.  The test does **not** assert the visual card order in
Board, and does not assert description text positions in Grid body text.

Reason: `page.locator("body").inner_text()` serialises the Grid table as a flat
string where column-header rows appear before data rows.  When two descriptions
share a common prefix (e.g. `"Reorder-A …"` / `"Reorder-B …"`), the header
cell order dominates the string index, making position-based assertions
unreliable without a stable row-scoped DOM selector.

A reliable browser reorder assertion would require:
- Querying each row's bounding box (`locator('[data-row-id=…]').bounding_box()`),
  or
- Using the AppFlowy Web DOM structure to scope description text to individual
  row elements.

This is deferred until the self-hosted AppFlowy Web DOM exposes a stable
`data-row-id` or equivalent attribute that Playwright can target.
