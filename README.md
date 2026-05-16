# AppFlowy MCP Toolkit

An MCP server, Python client, and CLI for controlling AppFlowy from AI agents.

It is built for the practical workflows agents need most: inspect workspaces, read
folder/page/database structure, create and move task cards, write typed database fields,
upload media, and verify changes against a disposable self-hosted AppFlowy stack before
touching real data.

Status: pre-1.0 release candidate. Core task, page/view, metadata, file-storage,
diagnostic, and guarded write paths are implemented with offline, self-hosted Docker,
and browser smoke coverage.

## Why This Exists

Most AppFlowy automation examples stop at a few REST calls. That is not enough for an
agent that needs to safely operate a real task board. AppFlowy has REST routes, collab
state, row ordering, typed database cells, file storage, and a web UI that can lag behind
the data plane.

This repo tries to make those edges explicit:

- local-first testing with disposable AppFlowy Docker
- writes disabled by default
- task-card helpers for create/update/move/delete
- typed database values for rich fields such as select, multi-select, checklist, time,
  summary, URL, checkbox, number, datetime, and media
- AppFlowy file upload/download/delete support for Media fields
- verification tools that distinguish API/collab truth from browser rendering
- documentation for deferred areas instead of pretending everything is solved

## Project Provenance

This project was implemented end-to-end by Ela, an AI coding agent, under human
supervision. The development process used a multi-agent strategy for bounded research,
implementation, and verification tasks, with final integration and release decisions
reviewed by a human maintainer.

## Current Scope

Implemented:

- MCP server: `appflowy-mcp-server`
- CLI: `appflowy-toolkit`
- Python client: `appflowy_mcp_toolkit`
- Workspaces, folder/page/view reads, database schema/rows, tasks, typed row writes,
  quick notes, search, file-storage metadata, v1 file upload/download/delete, and
  guarded page/view mutations.
- Self-hosted Docker test workflow using official AppFlowy-Cloud compose sources.

Intentionally deferred:

- No required Docker runtime for normal users; self-hosted tests are optional.
- No Notion migration.
- No broad delete/admin/invite tools.
- No publishing/sharing/member-management mutations in the first public slice.
- No AI/chat workflow automation yet.
- No personal workflow assumptions.
- No secrets, workspace IDs, emails, or private fixtures committed.

## Quick Start

```bash
python -m pip install -e '.[mcp]'
appflowy-toolkit health
appflowy-mcp-server
```

For development:

```bash
python -m pip install -e '.[dev,mcp,browser]'
scripts/test_all_local.sh
```

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
appflowy-toolkit upload-file-v1 --workspace-id <workspace_id> --parent-dir <parent_dir> --file-path ./spec.txt --execute
appflowy-toolkit download-file-v1 --workspace-id <workspace_id> --parent-dir <parent_dir> --file-id <file_id> --output ./spec.txt
appflowy-toolkit delete-file-v1 --workspace-id <workspace_id> --parent-dir <parent_dir> --file-id <file_id> --execute
appflowy-toolkit upload-media-file --workspace-id <workspace_id> --database-id <database_id> --file-path ./spec.txt --execute
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
appflowy-toolkit search --workspace-id <workspace_id> --query "project plan" --limit 5
appflowy-toolkit row-details --workspace-id <workspace_id> --database-id <database_id> --ids <row_id>
appflowy-toolkit collab-json --workspace-id <workspace_id> --object-id <database_id> --collab-type Database
appflowy-toolkit row-orders --workspace-id <workspace_id> --database-id <database_id>
appflowy-toolkit blob-diff --workspace-id <workspace_id> --database-id <database_id>
appflowy-toolkit verify-row --workspace-id <workspace_id> --database-id <database_id> --row-id <row_id>
appflowy-toolkit create-verified-row --workspace-id <workspace_id> --database-id <database_id> --cells-json '{"Description":"Test"}'
appflowy-toolkit create-typed-row --workspace-id <workspace_id> --database-id <database_id> --values-json '{"Description":"Test","Status":"Doing","Multiselect":["fast"]}'
appflowy-toolkit upsert-typed-row --workspace-id <workspace_id> --database-id <database_id> --pre-hash <stable_key> --values-json '{"Description":"Updated","Status":"Done"}'
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
- `docs/typed-field-coverage.md` - typed field/cell coverage status for richer task cards.
- `docs/self-hosted-test-plan.md` - how to run disposable local AppFlowy for destructive tests.
- `docs/release-checklist.md` - final checks before publishing or external handoff.

Do not use a real/private AppFlowy workspace for write tests. Use the self-hosted
Docker stack for the normal contributor test workflow.

For a full local release-style run, use:

```bash
scripts/test_all_local.sh
```

That command runs the offline unit suite, formatting/lint/type/build gates, starts the
disposable self-hosted AppFlowy Docker stack, seeds test credentials, and runs the
self-hosted and browser smoke tests. Plain `uv run pytest -q` intentionally skips
Docker/browser tests so the default suite stays safe on machines without AppFlowy
running. If Docker is installed but your user cannot access the daemon yet, run
`sudo -v` first or add the user to the Docker group.

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
- `appflowy_create_typed_database_row`
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
- `appflowy_upload_file_blob_v1`
- `appflowy_delete_file_blob_v1`
- `appflowy_upload_file_as_media`
- `appflowy_upsert_database_row`
- `appflowy_upsert_typed_database_row`
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
  explicit row-detail lookup by id may still resolve the old row object.

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

File storage coverage now includes read-only usage/metadata, v1 upload/download/delete
helpers, and a helper that uploads a local file and returns a typed Media-cell object:
`GET /api/file_storage/{workspace_id}/usage`,
`GET /api/file_storage/{workspace_id}/blobs`,
`GET /api/file_storage/{workspace_id}/metadata/{file_id}`, and
`GET /api/file_storage/{workspace_id}/v1/metadata/{parent_dir}/{file_id}` plus
`PUT` / `GET` / `DELETE` for
`/api/file_storage/{workspace_id}/v1/blob/{parent_dir}/{file_id}`. File writes remain
dry-run/gated by default. For database Media fields, the proven convention is
`parent_dir = database_id`; `upload-media-file` returns the object that can be used in
typed row values with `upload_type = Cloud`.

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

Current browser expectation is: login/Grid rendering should pass; MCP-created rows
are verified through REST/collab/blob-diff before the UI assertion. Depending on
AppFlowy Web rendering state, the row-rendering test may pass or record an expected
`xfail`. That is recorded as browser-rendering evidence, not hidden.

## Development

```bash
python -m pip install -e '.[dev,mcp]'
python -m pytest
python -m ruff format --check .
python -m ruff check .
python -m mypy src tests
```
