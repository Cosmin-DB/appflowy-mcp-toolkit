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
