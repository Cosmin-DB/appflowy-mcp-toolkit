# AppFlowy MCP Toolkit

A safe MCP server, Python client, and CLI for controlling AppFlowy from AI agents.

Covers the practical agent workflows: inspect workspaces and folders, create and move
task cards, write typed database fields, upload media, and verify changes before
touching real data. Writes are disabled by default.

> **0.2.0.** Core task-board, typed-field, media, page/view organization,
> publishing, template discovery, and published-page duplication paths are tested.
> Append Markdown to pages is supported. Full fetch/replace/block-level document
> editing is backlog.

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
appflowy-toolkit workflows
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

For local file uploads (`upload-file-v1`, `upload-media-file`), two additional
gates are required:

```bash
export APPFLOWY_ALLOW_LOCAL_FILE_READS=true
export APPFLOWY_ALLOWED_FILE_ROOTS=/path/to/safe/dir:/another/dir  # colon-sep on Linux/macOS
```

Files outside `APPFLOWY_ALLOWED_FILE_ROOTS` are rejected even when
`APPFLOWY_ALLOW_LOCAL_FILE_READS=true`.  Dry-run uses only `stat()` (no file
content is read) and still validates the path is inside allowed roots.

Rate limits are enabled by default. MCP server tool calls share one
process-wide limiter; CLI/direct client usage keeps a per-client limiter.
Defaults:
120 calls/min overall, 30 writes/min, 20 blob/collab/min, 8 concurrent.
Set `APPFLOWY_RATE_LIMIT_ENABLED=false` to disable, or tune individual
buckets with `APPFLOWY_RATE_LIMIT_CALLS_PER_MINUTE`,
`APPFLOWY_RATE_LIMIT_WRITES_PER_MINUTE`,
`APPFLOWY_RATE_LIMIT_BLOB_COLLAB_PER_MINUTE`,
`APPFLOWY_RATE_LIMIT_CONCURRENT_CALLS`.

---

## MCP server

```bash
# start the server (stdio transport, for use with any MCP client)
appflowy-mcp-server
```

The server is a standard MCP stdio server. Add it to any MCP client config using
the command and environment variables below:

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

Or use `uvx` without a local install:

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

Client-specific config file locations and schemas differ. The project only
promises the standard stdio command interface shown above unless a client recipe
is explicitly tested and documented.

---

## What is supported

| Area | Status | Validation evidence |
|---|---|---|
| Workspaces, user profile, server info | supported | unit-tested; CI |
| Folder / page / view reads | supported | unit-tested; self-hosted page lifecycle smoke |
| Database schema, rows, typed fields | supported | unit-tested; self-hosted tests; browser-tested typed fields |
| Task create / update / move / delete | supported | unit-tested; self-hosted tests; browser-tested Grid/Board lifecycle; human-verified visible AppFlowy Cloud card on 2026-05-18 |
| Select and multi-select field writes | supported | unit-tested; typed-field browser coverage where rendered by AppFlowy Web |
| Number, checkbox, URL, summary, time fields | supported | unit-tested; browser-tested typed field rendering |
| File storage metadata + v1 upload/download/delete | supported | unit-tested; Docker/self-hosted and AppFlowy Cloud single-file flow |
| Media field upload (returns typed cell object) | supported | Docker/self-hosted upload flow; typed Media cell coverage |
| Quick notes read/write | supported | unit-tested; AppFlowy Cloud create/update/delete smoke, but live list behavior needs follow-up |
| Full-text search | supported | unit-tested; depends on AppFlowy search service |
| Page/view organization (create, move, trash, restore) | supported | unit-tested; self-hosted page lifecycle smoke; limited browser validation |
| Row/card reorder (Yjs collab, requires collab writes gate) | supported with explicit opt-in | unit/offline Yjs tests; data-plane + browser presence coverage; exact visual order remains a documented gap |
| Board column reorder (Yjs collab) | supported with explicit opt-in | unit/offline Yjs tests; data-plane + browser presence coverage; exact visual order remains a documented gap |
| Row delete (Yjs collab, no REST endpoint in AppFlowy) | supported with explicit opt-in | unit/offline Yjs tests; browser lifecycle delete coverage |
| Raw append blocks to a page | supported; low-level, use append-page-markdown for Markdown input | route/unit coverage only; no polished document UI validation |
| Append Markdown to a page | supported; paragraphs, headings, lists, blockquotes converted to blocks | unit-tested; browser-tested visible page content; human-verified on AppFlowy Cloud 2026-05-18; full inline formatting is backlog |
| Polished document/page Markdown editing (fetch/replace/block edit) | not supported; backlog | not applicable |
| Block-level document editing: update/delete/move/insert blocks | not supported; backlog | not applicable |
| Publishing / public sharing | read metadata + publish/unpublish writes supported (gated) | unit-tested; browser-tested published public URL visibility; publish/unpublish human-verified on AppFlowy Cloud 2026-05-18 |
| Member / invite / access/admin mutations | not supported yet; safety-sensitive deferred work | not applicable |
| Templates | read-only category/creator/template discovery supported; published template instantiation supported (gated); arbitrary unpublished template instantiation not supported | unit-tested against pinned AppFlowy template-center and published-duplicate routes; browser-tested published-page instantiation; duplicate published page human-verified on AppFlowy Cloud 2026-05-18 |
| Import/export and migrations | not supported yet | not applicable |
| Comments, reminders, live cursors, presence | not supported yet | not applicable |
| AppFlowy AI / chat routes | not supported yet | not applicable |
| Broad generic collab/Yjs mutation tools | intentionally not supported | not applicable |

**Supported with explicit opt-in** means the feature works and is tested, but it
will not run live unless the caller sets the required safety flags
(`APPFLOWY_ALLOW_WRITES`, and for Yjs/collab paths
`APPFLOWY_ALLOW_COLLAB_WRITES`). Yjs helpers also need a local Node.js runtime.

Validation evidence is intentionally explicit. **Unit-tested** means offline test
coverage; **self-hosted/Docker** means a disposable AppFlowy stack was exercised;
**browser-tested** means AppFlowy Web was checked through Playwright; and
**human-verified** means a person confirmed the behavior in the real web UI. When
human validation changes, update this table in the same commit.

---

## CLI reference

```bash
appflowy-toolkit doctor              # offline install/env check
appflowy-toolkit doctor --check-appflowy  # also call AppFlowy health endpoint
appflowy-toolkit workflows           # safe operating paths for agents
appflowy-toolkit setup-check         # local Yjs/Node helper diagnostics
appflowy-toolkit health
appflowy-toolkit workspaces
appflowy-toolkit user-profile
appflowy-toolkit server-info
appflowy-toolkit template-categories
appflowy-toolkit templates --is-featured
appflowy-toolkit template --view-id <id>
appflowy-toolkit template-homepage --per-count 3
appflowy-toolkit published-pages --workspace-id <id>
appflowy-toolkit published-page-info --view-id <id>
appflowy-toolkit publish-page --workspace-id <id> --view-id <id> [--publish-name slug] [--execute]
appflowy-toolkit unpublish-page --workspace-id <id> --view-id <id> [--execute]
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

High-value MCP tools return both backwards-compatible text JSON and
`structuredContent` for clients that can consume typed results:
`appflowy_list_tasks`, `appflowy_get_database_rows`,
`appflowy_verify_database_row`, `appflowy_create_task`,
`appflowy_publish_page`, `appflowy_list_templates`, and
`appflowy_get_database_view_configs`. List-like structured payloads are
wrapped as `{"result": [...]}` because MCP structured content is a JSON
object.

Read-only tools (safe with no write gates):

`appflowy_health_check`, `appflowy_get_server_info`, `appflowy_get_user_profile`,
`appflowy_safe_workflows`, `appflowy_list_workspaces`, `appflowy_get_folder`,
`appflowy_list_databases`,
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
`appflowy_get_publish_namespace`, `appflowy_get_publish_default`,
`appflowy_list_published_pages`, `appflowy_get_published_page_info`,
`appflowy_list_file_storage_blobs`, `appflowy_get_file_metadata`,
`appflowy_get_file_metadata_v1`, `appflowy_list_template_categories`,
`appflowy_get_template_category`, `appflowy_list_template_creators`,
`appflowy_get_template_creator`, `appflowy_list_templates`,
`appflowy_get_template`, `appflowy_get_template_homepage`

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

Publish write tools (also require `APPFLOWY_ALLOW_PUBLISH_WRITES=true`; dry-run by default;
browser-tested against the local self-hosted stack where noted, and otherwise
unit-tested only):

`appflowy_publish_page`, `appflowy_unpublish_page`,
`appflowy_duplicate_published_page`, `appflowy_instantiate_template`

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
