# AppFlowy MCP Toolkit

A safe MCP server, Python client, and CLI for controlling AppFlowy from AI agents.

Covers the practical agent workflows: inspect workspaces and folders, create and move
task cards, write typed database fields, upload media, and verify changes before
touching real data. Writes are disabled by default.

> **0.1.0 - first public release.** Core task-board, typed-field, media, page/view
> organization, and diagnostic paths are tested. Polished document/page Markdown
> editing is tracked as backlog and is not yet supported.

---

## Install

```bash
# pipx (recommended for CLI use)
pipx install appflowy-mcp-toolkit

# or uv
uv tool install appflowy-mcp-toolkit
```

Verify the install:

```bash
appflowy-toolkit doctor
```

---

## Quick setup

Export credentials before running any command that talks to AppFlowy:

```bash
export APPFLOWY_BASE_URL=https://beta.appflowy.cloud   # or your self-hosted URL
export APPFLOWY_ACCESS_TOKEN=<your-personal-token>
```

Get a personal token at **AppFlowy > Settings > Cloud Settings > Token**.

Check the connection:

```bash
appflowy-toolkit doctor --check-appflowy
appflowy-toolkit health
appflowy-toolkit workspaces
```

For write operations, also set:

```bash
export APPFLOWY_ALLOW_WRITES=true
export APPFLOWY_ALLOW_COLLAB_WRITES=true   # required for Yjs-based updates/deletes
```

---

## MCP server

```bash
# start the server (stdio transport, for use with any MCP client)
appflowy-mcp-server
```

The server is a standard MCP stdio server. Add it to your MCP client config, for
example in Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "appflowy": {
      "command": "appflowy-mcp-server",
      "env": {
        "APPFLOWY_BASE_URL": "https://beta.appflowy.cloud",
        "APPFLOWY_ACCESS_TOKEN": "<your-token>"
      }
    }
  }
}
```

Or with `uvx` without a local install:

```json
{
  "mcpServers": {
    "appflowy": {
      "command": "uvx",
      "args": ["--from", "appflowy-mcp-toolkit", "appflowy-mcp-server"],
      "env": {
        "APPFLOWY_BASE_URL": "https://beta.appflowy.cloud",
        "APPFLOWY_ACCESS_TOKEN": "<your-token>"
      }
    }
  }
}
```

For Cursor, Windsurf, or other MCP clients, use the same `command`/`env` pattern
in their respective config files.

---

## What is supported

| Area | Status |
|---|---|
| Workspaces, user profile, server info | supported |
| Folder / page / view reads | supported |
| Database schema, rows, typed fields | supported |
| Task create / update / move / delete | supported |
| Select and multi-select field writes | supported |
| Number, checkbox, URL, summary, time fields | supported |
| File storage metadata + v1 upload/download/delete | supported |
| Media field upload (returns typed cell object) | supported |
| Quick notes read/write | supported |
| Full-text search | supported |
| Page/view organization (create, move, trash, restore) | supported |
| Row/card reorder (Yjs collab, requires collab writes gate) | supported with explicit opt-in |
| Board column reorder (Yjs collab) | supported with explicit opt-in |
| Row delete (Yjs collab, no REST endpoint in AppFlowy) | supported with explicit opt-in |
| Raw append blocks to a page | low-level primitive, not a polished document editor |
| Polished document/page Markdown editing | not supported yet; backlog |
| Block-level document editing: update/delete/move/insert blocks | not supported yet; backlog |
| Publishing / public sharing | not supported yet; safety-sensitive deferred work |
| Member / invite / access/admin mutations | not supported yet; safety-sensitive deferred work |
| Templates | not supported yet; read-only discovery is a candidate |
| Import/export and migrations | not supported yet |
| Comments, reminders, live cursors, presence | not supported yet |
| AppFlowy AI / chat routes | not supported yet |
| Broad generic collab/Yjs mutation tools | intentionally not supported |

**Supported with explicit opt-in** means the feature works and is tested, but it
will not run live unless the caller sets the required safety flags
(`APPFLOWY_ALLOW_WRITES`, and for Yjs/collab paths
`APPFLOWY_ALLOW_COLLAB_WRITES`). Yjs helpers also need a local Node.js runtime.

---

## CLI reference

```bash
appflowy-toolkit doctor              # offline install/env check
appflowy-toolkit doctor --check-appflowy  # also call AppFlowy health endpoint
appflowy-toolkit setup-check         # local Yjs/Node helper diagnostics
appflowy-toolkit health
appflowy-toolkit workspaces
appflowy-toolkit user-profile
appflowy-toolkit server-info
appflowy-toolkit folder --workspace-id <id> --depth 2
appflowy-toolkit databases --workspace-id <id>
appflowy-toolkit fields  --workspace-id <id> --database-id <id>
appflowy-toolkit search  --workspace-id <id> --query "..."
```

Most write commands accept `--execute` to leave dry-run mode. Without `--execute`
the command prints what it *would* do.

Full command list: `appflowy-toolkit --help`

---

## MCP tools - quick reference

Read-only tools (safe with no write gates):

`appflowy_health_check`, `appflowy_get_server_info`, `appflowy_get_user_profile`,
`appflowy_list_workspaces`, `appflowy_get_folder`, `appflowy_list_databases`,
`appflowy_get_database_schema`, `appflowy_get_database_rows`,
`appflowy_list_database_row_ids`, `appflowy_list_updated_database_rows`,
`appflowy_list_select_options`, `appflowy_list_tasks`, `appflowy_search_tasks`,
`appflowy_search_documents`, `appflowy_list_quick_notes`,
`appflowy_get_database_row_orders`, `appflowy_verify_database_row`,
`appflowy_get_database_blob_diff`, `appflowy_get_collab_json`,
`appflowy_list_recent_views`, `appflowy_list_favorite_views`,
`appflowy_list_trash_views`, `appflowy_get_page_view`,
`appflowy_get_workspace_settings`, `appflowy_list_workspace_members`,
`appflowy_get_workspace_usage`, `appflowy_get_file_storage_usage`,
`appflowy_list_file_storage_blobs`, `appflowy_get_file_metadata`,
`appflowy_get_file_metadata_v1`

Write tools (dry-run by default; set `APPFLOWY_ALLOW_WRITES=true` to execute):

`appflowy_create_task`, `appflowy_update_task`, `appflowy_update_task_by_name`,
`appflowy_move_task`, `appflowy_move_task_by_name`, `appflowy_move_task_by_id`,
`appflowy_delete_task`, `appflowy_delete_task_by_name`,
`appflowy_create_database_row`, `appflowy_create_verified_database_row`,
`appflowy_create_typed_database_row`, `appflowy_upsert_database_row`,
`appflowy_upsert_typed_database_row`, `appflowy_upsert_managed_task`,
`appflowy_upsert_verified_managed_task`, `appflowy_move_managed_task_status`,
`appflowy_update_database_row_by_id`, `appflowy_create_database_field`,
`appflowy_create_space`, `appflowy_update_space`,
`appflowy_create_folder_view`, `appflowy_create_page_view`,
`appflowy_update_page_view`, `appflowy_rename_page_view`,
`appflowy_move_page_view`, `appflowy_trash_page_view`,
`appflowy_restore_page_view`, `appflowy_delete_trashed_page_view`,
`appflowy_favorite_page_view`, `appflowy_remove_page_icon`,
`appflowy_append_blocks_to_page`, `appflowy_reorder_favorite_page_view`,
`appflowy_duplicate_page_view`, `appflowy_create_page_database_view`,
`appflowy_add_recent_pages`, `appflowy_restore_all_pages_from_trash`,
`appflowy_delete_all_pages_from_trash`,
`appflowy_create_quick_note`, `appflowy_update_quick_note`,
`appflowy_delete_quick_note`,
`appflowy_upload_file_blob_v1`, `appflowy_delete_file_blob_v1`,
`appflowy_upload_file_as_media`

Experimental collab write tools (also require `APPFLOWY_ALLOW_COLLAB_WRITES=true`
and Node.js 18+ with `npm install` run in `src/appflowy_mcp_toolkit/collab/`):

`appflowy_delete_database_row`, `appflowy_reorder_database_row`,
`appflowy_reorder_database_column`

---

## Task workflow notes

`appflowy_create_task` uses AppFlowy's normal row-create route. Browser tests showed
that `pre_hash` upserts can verify through REST/collab state while failing to appear
in the Grid view. Use `create_task` for new cards; use `update_task` or `move_task`
when you have a `task_key`.

For rows created manually in AppFlowy, use `appflowy_move_task_by_id` or
`appflowy_update_database_row_by_id`; REST `pre_hash` upsert cannot target an
arbitrary existing `row_id`.

For assistant workflows where a human names a card, use `appflowy_search_tasks`
first (with `exact` or `contains` mode), then call an explicit operation with the
resolved `row_id`. `update_task_by_name`, `move_task_by_name`, and
`delete_task_by_name` refuse to act when more than one card matches.

---

## For AI agents / contributor onboarding

Start with:

- `AGENTS.md` - working rules, safety boundaries, test gates
- `docs/appflowy-coverage-matrix.md` - implemented, candidate, and deferred surface
- `docs/rest-vs-collab.md` - when to use REST vs Yjs collab
- `docs/browser-ui-acceptance.md` - why Grid/Board rendering is tested separately
- `docs/typed-field-coverage.md` - rich field/cell coverage
- `docs/self-hosted-test-plan.md` - local Docker testing
- `docs/release-checklist.md` - gates before publishing

Do not use a real/private AppFlowy workspace for write tests. Use the self-hosted
Docker stack described in `docs/self-hosted-test-plan.md`.

---

## Self-hosted AppFlowy tests (Docker)

```bash
scripts/appflowy_test_env_up.sh
python scripts/appflowy_test_seed.py
set -a; source .env.selfhosted.generated; set +a
APPFLOWY_SELFHOSTED_TESTS=true uv run pytest tests/selfhosted -q -s
scripts/appflowy_test_env_down.sh --volumes
```

Optional browser smoke:

```bash
APPFLOWY_BROWSER_TESTS=true uv run --extra browser pytest tests/browser -q -s
```

---

## Development

```bash
git clone https://github.com/Cosmin-DB/appflowy-mcp-toolkit
cd appflowy-mcp-toolkit
uv sync --extra dev --extra browser
uv run pytest -q          # offline unit tests only
scripts/test_all_local.sh # full battery including Docker
```

---

## Why this exists

Most AppFlowy automation examples stop at a few REST calls. That is not enough for an
agent that needs to safely operate a real task board. AppFlowy has REST routes, collab
state, row ordering, typed database cells, file storage, and a web UI that can lag
behind the data plane.

This project makes those edges explicit: local-first testing with disposable Docker,
writes disabled by default, typed helpers with data-plane verification, and documented
deferred areas instead of pretending everything is solved.

Built by **Ela** (AI agent) with human supervision from Cosmin.
