# AppFlowy MCP Toolkit

A local-first, read-first MCP toolkit for AppFlowy Cloud and self-hosted AppFlowy.

Status: pre-1.0 release candidate for local/public review. Core task, page/view,
metadata, diagnostic, and guarded write paths are implemented with offline,
live, self-hosted, and browser smoke coverage. Publication still requires an
explicit final review/approval.

## Goals

- Reusable Python client for AppFlowy REST API.
- CLI inspection commands for debugging without an MCP client.
- Read-only MCP tools plus task-facing write tools, disabled by default.
- Cloud and self-host friendly via `APPFLOWY_BASE_URL`.

## Non-goals for the first version

- No required Docker runtime for normal users; self-hosted tests are optional.
- No Notion migration.
- No broad delete/admin/invite tools.
- No personal workflow assumptions.
- No secrets, workspace IDs, emails, or private fixtures committed.

## Environment

Copy `.env.example` outside or to `.env` locally. Do not commit real secrets.

```bash
APPFLOWY_BASE_URL=http://localhost
APPFLOWY_ACCESS_TOKEN=...
APPFLOWY_REFRESH_TOKEN=...
```

## CLI

```bash
appflowy-toolkit health
appflowy-toolkit setup-check  # local Node/npm/Yjs helper diagnostics
appflowy-toolkit server-info
appflowy-toolkit user-profile
appflowy-toolkit user-workspace-info
appflowy-toolkit workspaces
appflowy-toolkit workspace-settings --workspace-id <workspace_id>
appflowy-toolkit workspace-members --workspace-id <workspace_id>
appflowy-toolkit workspace-usage --workspace-id <workspace_id>
appflowy-toolkit create-space --workspace-id <workspace_id> --name "Engineering"
appflowy-toolkit update-space --workspace-id <workspace_id> --view-id <space_view_id> --name "Engineering"
appflowy-toolkit file-storage-usage --workspace-id <workspace_id>
appflowy-toolkit file-storage-blobs --workspace-id <workspace_id>
appflowy-toolkit file-metadata --workspace-id <workspace_id> --file-id <file_id>
appflowy-toolkit file-metadata-v1 --workspace-id <workspace_id> --parent-dir <parent_dir> --file-id <file_id>
appflowy-toolkit folder --workspace-id <workspace_id> --depth 2
appflowy-toolkit create-folder --workspace-id <workspace_id> --parent-view-id <parent_view_id> --name "Folder"
appflowy-toolkit recent --workspace-id <workspace_id>
appflowy-toolkit favorites --workspace-id <workspace_id>
appflowy-toolkit trash --workspace-id <workspace_id>
appflowy-toolkit page-view --workspace-id <workspace_id> --view-id <view_id>
appflowy-toolkit create-page --workspace-id <workspace_id> --parent-view-id <parent_view_id> --name "New page"
appflowy-toolkit rename-page --workspace-id <workspace_id> --view-id <view_id> --name "Renamed page"
appflowy-toolkit favorite-page --workspace-id <workspace_id> --view-id <view_id>
appflowy-toolkit remove-page-icon --workspace-id <workspace_id> --view-id <view_id>
appflowy-toolkit append-page-blocks --workspace-id <workspace_id> --view-id <view_id> --blocks-json '[{}]'
appflowy-toolkit move-page --workspace-id <workspace_id> --view-id <view_id> --new-parent-view-id <parent_view_id>
appflowy-toolkit reorder-favorite-page --workspace-id <workspace_id> --view-id <view_id>
appflowy-toolkit duplicate-page --workspace-id <workspace_id> --view-id <view_id>
appflowy-toolkit create-page-database --workspace-id <workspace_id> --view-id <view_id> --layout 1
appflowy-toolkit trash-page --workspace-id <workspace_id> --view-id <view_id>
appflowy-toolkit restore-page --workspace-id <workspace_id> --view-id <view_id>
appflowy-toolkit delete-trash-page --workspace-id <workspace_id> --view-id <view_id>
appflowy-toolkit add-recent-pages --workspace-id <workspace_id> --view-ids <view_id>
appflowy-toolkit restore-all-pages --workspace-id <workspace_id>
appflowy-toolkit delete-all-trash-pages --workspace-id <workspace_id>
appflowy-toolkit databases --workspace-id <workspace_id>
appflowy-toolkit fields --workspace-id <workspace_id> --database-id <database_id>
appflowy-toolkit create-field --workspace-id <workspace_id> --database-id <database_id> --name "Priority" --field-type 0
appflowy-toolkit rows --workspace-id <workspace_id> --database-id <database_id>
appflowy-toolkit updated-rows --workspace-id <workspace_id> --database-id <database_id> --after 2026-05-16T10:00:00Z
appflowy-toolkit quick-notes --workspace-id <workspace_id> --search-term "apple" --limit 10
appflowy-toolkit create-quick-note --workspace-id <workspace_id> --data-json '[{"type":"paragraph","delta":{"insert":"Note"}}]'
appflowy-toolkit update-quick-note --workspace-id <workspace_id> --quick-note-id <quick_note_id> --data-json '[{"type":"paragraph","delta":{"insert":"Updated"}}]'
appflowy-toolkit delete-quick-note --workspace-id <workspace_id> --quick-note-id <quick_note_id>
appflowy-toolkit search --workspace-id <workspace_id> --query "roadmap" --limit 5
appflowy-toolkit row-details --workspace-id <workspace_id> --database-id <database_id> --ids <row_id>
appflowy-toolkit collab-json --workspace-id <workspace_id> --object-id <database_id> --collab-type Database
appflowy-toolkit row-orders --workspace-id <workspace_id> --database-id <database_id>
appflowy-toolkit blob-diff --workspace-id <workspace_id> --database-id <database_id>
appflowy-toolkit verify-row --workspace-id <workspace_id> --database-id <database_id> --row-id <row_id>
appflowy-toolkit create-verified-row --workspace-id <workspace_id> --database-id <database_id> --cells-json '{"Description":"Test"}'
appflowy-toolkit tasks --workspace-id <workspace_id> --database-id <database_id>
appflowy-toolkit create-task --workspace-id <workspace_id> --database-id <database_id> --task-key <stable_key> --description "Test"
appflowy-toolkit update-task --workspace-id <workspace_id> --database-id <database_id> --task-key <stable_key> --status "Doing"
appflowy-toolkit move-task --workspace-id <workspace_id> --database-id <database_id> --task-key <stable_key> --status "Done"
appflowy-toolkit delete-task --workspace-id <workspace_id> --database-id <database_id> --row-id <row_id>
appflowy-toolkit managed-task-verified --workspace-id <workspace_id> --database-id <database_id> --task-key <stable_key> --description "Test"

# Experimental: Yjs-based row delete (requires Node.js 18+ and npm install in collab/)
appflowy-toolkit delete-row --workspace-id <workspace_id> --database-id <database_id> --row-id <row_id>
appflowy-toolkit delete-row ... --execute  # live write; also needs APPFLOWY_ALLOW_WRITES=true and APPFLOWY_ALLOW_COLLAB_WRITES=true
```

## MCP server

```bash
appflowy-mcp-server
```

## For AI Agents

Start with these files:

- `AGENTS.md` - working rules, safety boundaries, and test gates for agents.
- `README.md` - user-facing install, CLI, MCP tools, and known limitations.
- `docs/appflowy-coverage-matrix.md` - implemented, candidate, and deferred AppFlowy areas.
- `docs/browser-ui-acceptance.md` - why browser rendering is tested separately from API/collab truth.
- `docs/self-hosted-test-plan.md` - how to run disposable local AppFlowy for destructive tests.
- `docs/release-checklist.md` - final checks before publishing or external handoff.

Do not use a real/private AppFlowy workspace for write tests. Use the self-hosted
Docker stack for the normal contributor test workflow.

Read-only tools:

- `appflowy_health_check`
- `appflowy_get_server_info`
- `appflowy_get_user_profile`
- `appflowy_get_user_workspace_info`
- `appflowy_list_workspaces`
- `appflowy_get_workspace_settings`
- `appflowy_list_workspace_members`
- `appflowy_get_workspace_usage`
- `appflowy_get_file_storage_usage`
- `appflowy_list_file_storage_blobs`
- `appflowy_get_file_metadata`
- `appflowy_get_file_metadata_v1`
- `appflowy_get_folder`
- `appflowy_list_recent_views`
- `appflowy_list_favorite_views`
- `appflowy_list_trash_views`
- `appflowy_get_page_view`
- `appflowy_list_databases`
- `appflowy_get_database_schema`
- `appflowy_list_database_row_ids`
- `appflowy_list_updated_database_rows`
- `appflowy_list_quick_notes`
- `appflowy_search_documents`
- `appflowy_get_database_rows`
- `appflowy_list_select_options`
- `appflowy_get_collab_json`
- `appflowy_get_database_row_orders`
- `appflowy_get_database_blob_diff`
- `appflowy_list_tasks`
- `appflowy_verify_database_row`

Write tools exist for controlled testing, but dry-run by default and require
`APPFLOWY_ALLOW_WRITES=true` for real mutations:

- `appflowy_create_database_row`
- `appflowy_create_verified_database_row`
- `appflowy_create_database_field`
- `appflowy_create_space`
- `appflowy_update_space`
- `appflowy_create_folder_view`
- `appflowy_create_page_view`
- `appflowy_update_page_view`
- `appflowy_rename_page_view`
- `appflowy_favorite_page_view`
- `appflowy_remove_page_icon`
- `appflowy_append_blocks_to_page`
- `appflowy_move_page_view`
- `appflowy_reorder_favorite_page_view`
- `appflowy_duplicate_page_view`
- `appflowy_create_page_database_view`
- `appflowy_trash_page_view`
- `appflowy_restore_page_view`
- `appflowy_delete_trashed_page_view`
- `appflowy_add_recent_pages`
- `appflowy_restore_all_pages_from_trash`
- `appflowy_delete_all_pages_from_trash`
- `appflowy_create_task`
- `appflowy_update_task`
- `appflowy_move_task`
- `appflowy_delete_task`
- `appflowy_create_quick_note`
- `appflowy_update_quick_note`
- `appflowy_delete_quick_note`
- `appflowy_upsert_database_row`
- `appflowy_upsert_managed_task`
- `appflowy_upsert_verified_managed_task`
- `appflowy_move_managed_task_status`

Task-facing tools are the preferred public workflow for board-like task databases.
`create_task`, `update_task`, and `move_task` use a caller-supplied stable
`task_key`, mapped to AppFlowy's `pre_hash`, and verify the resulting data-plane
state. `delete_task` currently requires the AppFlowy `row_id` returned by create/list
because there is no confirmed safe lookup-by-`pre_hash` delete endpoint.

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
endpoint. Row/card deletion in AppFlowy Web is a collab/Yjs update. The
`appflowy_delete_database_row` tool implements this path experimentally; it has been
tested against disposable self-hosted workspaces, but remains
opt-in and is not yet recommended for production use.

Board-rendering investigation: AppFlowy Web also calls a binary `blob/diff` endpoint
to seed row documents before rendering database views. `blob-diff` /
`appflowy_get_database_blob_diff` decodes that response into a safe summary (row ids,
operation types, RID values and doc-state byte counts) without exposing raw row document
state. This is diagnostic only; it does not mutate AppFlowy.

File storage coverage is metadata-only for now. The toolkit exposes read-only usage,
blob metadata listing, and v0/v1 metadata lookup routes:
`GET /api/file_storage/{workspace_id}/usage`,
`GET /api/file_storage/{workspace_id}/blobs`,
`GET /api/file_storage/{workspace_id}/metadata/{file_id}`, and
`GET /api/file_storage/{workspace_id}/v1/metadata/{parent_dir}/{file_id}`. Upload,
delete, and raw blob download endpoints are intentionally not implemented in this
slice.

Known AppFlowy Web limitation: Board rendering can be stale even when a row is already
present in REST and collab state. In local browser testing, verified rows can still
fail to render in AppFlowy Web during the browser pass.
Use `verify-row` / `appflowy_verify_database_row` for data-plane verification; use
browser tests separately for UI rendering.

## Self-Hosted AppFlowy Tests

The repo includes an optional self-hosted test workflow under
[`docker/appflowy-test/`](docker/appflowy-test/). It uses the official
`AppFlowy-IO/AppFlowy-Cloud` compose project at a pinned revision instead of vendoring
AppFlowy into this repo.

```bash
scripts/appflowy_test_env_up.sh
python scripts/appflowy_test_seed.py
set -a
source .env.selfhosted.generated
set +a
APPFLOWY_SELFHOSTED_TESTS=true uv run pytest tests/selfhosted -q
scripts/appflowy_test_env_down.sh --volumes
```

Self-hosted tests are destructive and must only target the local disposable stack.
The workflow has been validated against the pinned Docker stack; see
[`docs/self-hosted-test-plan.md`](docs/self-hosted-test-plan.md) for current pins,
seed behavior, and remaining UI/browser work.

Optional browser smoke against the local stack:

```bash
set -a
source .env.selfhosted.generated
set +a
APPFLOWY_BROWSER_TESTS=true uv run --extra browser pytest tests/browser -q -s
```

Current browser expectation is `1 passed, 1 xfailed`: login/Grid rendering passes;
MCP-created rows are verified through REST/collab/blob-diff, but this AppFlowy Web
build may still fail to render the verified row in Board/Grid during the browser pass.
That is recorded as browser-rendering evidence, not hidden.

## Development

```bash
python -m pip install -e '.[dev,mcp]'
python -m pytest
python -m ruff format --check .
python -m ruff check .
python -m mypy src tests
```
