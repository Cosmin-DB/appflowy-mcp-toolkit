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

## Development

```bash
python -m pip install -e '.[dev,mcp]'
python -m pytest
python -m ruff format --check .
python -m ruff check .
python -m mypy src tests
```
