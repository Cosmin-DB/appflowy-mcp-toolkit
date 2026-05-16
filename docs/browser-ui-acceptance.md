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
8. Delete the task through `appflowy_delete_task --execute` using the returned `row_id`;
   verify absence from row orders and REST row list.

Expected current behavior:

- Data-plane create/update/move/delete should pass.
- Board may hide cards after refresh until Grid is opened and Board is revisited. Treat
  that as a browser/UI finding, not an MCP mutation failure, unless REST/collab verification
  also fails.

Future automation can wrap this checklist with Playwright/OpenClaw browser control, but it
should keep two result channels: `data_plane` and `browser_rendering`.

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
