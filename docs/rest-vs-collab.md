# REST vs Collab Writes

AppFlowy has two write surfaces that look similar from the UI but behave very
differently from an automation client.

This toolkit deliberately uses both. REST stays the default. Collab/Yjs is used
only for the gaps where AppFlowy Web itself does not use a normal REST row-update
route.

## The Short Rule

- Use **REST** for reads, normal row creation, typed row creation, file storage,
  page/view routes, quick notes, and MCP-managed task upserts.
- Use **task_key / pre_hash** when the agent owns the logical task and wants
  stable create-or-update behavior.
- Use **row_id + collab** when the row already exists in AppFlowy and the user or
  browser created it manually.
- Use **collab delete** when removing a row from database views; there is no
  confirmed public REST delete-row endpoint.
- Use **database collab** for board column lifecycle operations. A board column
  is a select option on the grouped field, usually `Status`, plus a visible
  group entry in the board view. The supported lifecycle today is add, rename,
  hide and show.
- Use **read-only database collab diagnostics** for view configuration. Filters,
  sorts, board groups, field visibility/width and layout settings live on each
  database view inside the Database collab document.

## Why This Is Confusing

AppFlowy exposes row creation/upsert through REST:

- `POST /api/workspace/{workspace_id}/database/{database_id}/row`
- `PUT /api/workspace/{workspace_id}/database/{database_id}/row`

The `PUT` route does not update an arbitrary existing row id. It accepts
`pre_hash`. AppFlowy's server hashes `workspace_id + database_id + pre_hash`
into a deterministic row id.

That is useful for agent-owned tasks:

```text
task_key -> pre_hash -> deterministic AppFlowy row id
```

But rows created manually in AppFlowy Web do not come from our `task_key`. They
have an existing arbitrary `row_id`. Passing a new `pre_hash` would create or
upsert a different deterministic row, not mutate the manual row.

For those manual rows, AppFlowy Web updates the row's `DatabaseRow` collab
document. The relevant shape is the row document's `data.cells` map:

```text
DatabaseRow collab object
  data
    cells
      <field_id>
        field_type
        data
        last_modified
```

Select fields store option ids in collab state, while REST typed writes can
accept option names. That is why the toolkit has separate normalization for
collab row updates.

## Which Tool Should An Agent Use?

| Situation | Use | Reason |
|---|---|---|
| Read workspaces, folders, databases, rows, fields, tasks | REST tools | Stable, simple, low risk |
| Create a new task owned by the agent | `create_task` / `appflowy_create_task` | Uses `task_key` and verifies the data plane |
| Update or move a task previously created with `task_key` | `update_task` / `move_task` | REST `pre_hash` path is deterministic and idempotent |
| Update a row created manually in AppFlowy Web | `update-row-by-id` / `appflowy_update_database_row_by_id` | REST cannot target arbitrary existing row ids |
| Move a manually-created task/card by row id | `move-task-by-id` / `appflowy_move_task_by_id` | Thin wrapper over collab row update for Status |
| Add a board column/status option | `add-select-option` / `appflowy_add_select_option` | Board columns are stored in Database collab schema, not as rows |
| Rename a board column/status option | `rename-select-option` / `appflowy_rename_select_option` | Renames the select option in Database collab |
| Hide/show a board column/status option | `hide-select-option`, `show-select-option` / `appflowy_hide_select_option`, `appflowy_show_select_option` | Toggles board group visibility for the option |
| Inspect filters/sorts/groups/field widths | `view-configs` / `appflowy_get_database_view_configs` | View settings are stored in Database collab JSON |
| Delete a row/card | `delete-row` / `appflowy_delete_database_row` | AppFlowy Web deletion is collab row-order mutation |
| Delete/remove a board column/status option | Not implemented | Unsafe until the toolkit can prove how rows using that option are reassigned or cleared |
| Reorder cards precisely inside a view/column | Not implemented yet | Needs separate row_orders collab mutation design |

## Safety Gates

Live collab writes require both flags:

```bash
APPFLOWY_ALLOW_WRITES=true
APPFLOWY_ALLOW_COLLAB_WRITES=true
```

They also require Node.js 18+ and the local Yjs helper dependency:

```bash
cd src/appflowy_mcp_toolkit/collab
npm install
```

Dry-run remains the default. The Node helper receives only binary collab bytes
and a mutation payload. It receives no tokens and performs no network access;
Python owns authentication and the final `web-update` POST.

## Current Collab Write Coverage

Implemented:

- delete database row from view row orders
- update existing `DatabaseRow` cells by `row_id`
- move an existing/manual task by setting its Status field through `row_id`
- add, rename, hide and show select options, including board Status columns,
  through Database collab
- read-only extraction of Database view configuration: `layout_settings`,
  `filters`, `sorts`, `group_settings`, `field_settings`,
  `field_orders` and row-order counts

Not implemented yet:

- remove/delete select options or board columns; existing rows may still store
  the removed option id, and AppFlowy Web's reassignment/cleanup behavior needs
  its own Docker and browser proof before exposing a destructive schema write
- exact card reorder inside a view/column
- updates to filters, sorts, field visibility/width, or layout settings
- generic document/block collab editing
- broad arbitrary collab object mutation

## Database View Configuration Shape

Current AppFlowy source represents a `DatabaseView` with `layout_settings`,
`filters`, `group_settings`, `sorts`, `row_orders`, `field_orders` and
`field_settings` in the Database collab document. The cloud page-view creation
path fills those same fields when creating board/grid/calendar views. Field
settings use keys such as `visibility`, `width` and
`wrap` (normalized by the toolkit as `wrap_cell_content`); board groups include a grouped `field_id`, `ty` field
type and per-group `id`/visibility entries.

The toolkit now exposes that shape as a read-only summary. It deliberately does
not update filters/sorts/layout/field settings yet: those are structural Yjs
view mutations and need a separate unit -> Docker/self-hosted -> disposable
cloud proof before being offered as live writes.

## Practical Guidance

If you are an agent, do not guess.

1. If the user gives you a `task_key` or you created the task, use the managed
   task tools.
2. If the user points at an existing UI-created card, first list/search rows and
   obtain the `row_id`.
3. Then use `move-task-by-id` or `update-row-by-id`.
4. Verify with `verify-row`.
5. Treat AppFlowy Web Board rendering as secondary; it can lag until Grid/refresh
   warms the page.
