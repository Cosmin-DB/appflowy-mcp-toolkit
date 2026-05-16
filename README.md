# AppFlowy MCP Toolkit

A local-first, read-first MCP toolkit for AppFlowy Cloud and self-hosted AppFlowy.

Status: early local draft. Not ready for public release yet.

## Goals

- Reusable Python client for AppFlowy REST API.
- CLI inspection commands for debugging without an MCP client.
- Read-only MCP tools first.
- Safe write tools later, disabled by default.
- Cloud and self-host friendly via `APPFLOWY_BASE_URL`.

## Non-goals for the first version

- No Docker/compose until deployment actually needs it.
- No Notion migration.
- No broad delete/admin/invite tools.
- No personal workflow assumptions.
- No secrets, workspace IDs, emails, or private fixtures committed.

## Environment

Copy `.env.example` outside or to `.env` locally. Do not commit real secrets.

```bash
APPFLOWY_BASE_URL=https://beta.appflowy.cloud
APPFLOWY_ACCESS_TOKEN=...
APPFLOWY_REFRESH_TOKEN=...
```

## CLI

```bash
appflowy-toolkit workspaces
appflowy-toolkit folder --workspace-id <workspace_id> --depth 2
appflowy-toolkit databases --workspace-id <workspace_id>
appflowy-toolkit fields --workspace-id <workspace_id> --database-id <database_id>
appflowy-toolkit rows --workspace-id <workspace_id> --database-id <database_id>
appflowy-toolkit row-details --workspace-id <workspace_id> --database-id <database_id> --ids <row_id>
appflowy-toolkit collab-json --workspace-id <workspace_id> --object-id <database_id> --collab-type Database
appflowy-toolkit row-orders --workspace-id <workspace_id> --database-id <database_id>

# Experimental: Yjs-based row delete (requires Node.js 18+ and npm install in collab/)
appflowy-toolkit delete-row --workspace-id <workspace_id> --database-id <database_id> --row-id <row_id>
appflowy-toolkit delete-row ... --execute  # live write; also needs APPFLOWY_ALLOW_WRITES=true and APPFLOWY_ALLOW_COLLAB_WRITES=true
```

## MCP server

```bash
appflowy-mcp-server
```

Initial tools are read-only:

- `appflowy_health_check`
- `appflowy_list_workspaces`
- `appflowy_get_folder`
- `appflowy_list_databases`
- `appflowy_get_database_schema`
- `appflowy_list_database_row_ids`
- `appflowy_get_database_rows`
- `appflowy_list_select_options`
- `appflowy_get_collab_json`
- `appflowy_get_database_row_orders`

Write tools exist for controlled testing, but dry-run by default and require
`APPFLOWY_ALLOW_WRITES=true` for real mutations:

- `appflowy_create_database_row`
- `appflowy_upsert_database_row`
- `appflowy_upsert_managed_task`
- `appflowy_move_managed_task_status`

Experimental write tool (dry-run by default; requires `APPFLOWY_ALLOW_WRITES=true` **and**
`APPFLOWY_ALLOW_COLLAB_WRITES=true`; requires Node.js 18+ with `npm install` in
`src/appflowy_mcp_toolkit/collab/`):

- `appflowy_delete_database_row` — deletes a row from all views via Yjs collab
  mutation. This is the only confirmed delete path; AppFlowy Web does not expose
  a REST row-delete endpoint. **Not yet proven for all board create/edit/move
  scenarios.** The current verification means absent from database view row lists;
  explicit row-detail lookup by id may still resolve the old row object. See
  `docs/collab-driver-plan.md` for the full M6 status.

Current API limitation: public AppFlowy REST does not expose a confirmed row-delete
endpoint. Row/card deletion in AppFlowy Web is a collab/Yjs update. The `appflowy_delete_database_row`
tool implements this path experimentally; it has been live-tested against a disposable
workspace but is not yet recommended for production use.

## Development

```bash
python -m pip install -e '.[dev,mcp]'
python -m pytest
python -m ruff format --check .
python -m ruff check .
python -m mypy src tests
```
