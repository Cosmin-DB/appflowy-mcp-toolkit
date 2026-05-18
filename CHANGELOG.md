# Changelog

All notable changes to `appflowy-mcp-toolkit` are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Added / Changed

- **Local file upload hardening** (`upload_local_file_blob_v1`, `upload_file_as_media`):
  - New `AppFlowyConfig` fields: `allow_local_file_reads` (from
    `APPFLOWY_ALLOW_LOCAL_FILE_READS`) and `allowed_file_roots` (from
    `APPFLOWY_ALLOWED_FILE_ROOTS`, `os.pathsep`-separated).
  - New `AppFlowyClient._require_local_file_read_allowed(path)` helper enforces:
    1. `APPFLOWY_ALLOW_LOCAL_FILE_READS=true` required.
    2. `APPFLOWY_ALLOWED_FILE_ROOTS` must be set and non-empty.
    3. `realpath(path)` must be inside one of the allowed roots (prevents
       path traversal and symlink escape).
  - `upload_local_file_blob_v1` dry-run now uses `stat()` only — no
    `read_bytes()` call, no network call.
  - Both gates apply equally to `upload_file_as_media` via delegation.
  - 17 new unit tests in `tests/unit/test_local_upload_hardening.py`.

- **In-process rate limiting**: `AppFlowyClient` now enforces sliding-window
  buckets at the network layer (all four request methods).  Defaults:
  120 calls/min overall, 30 writes/min, 20 blob\/collab/min, 8 concurrent.
  Controlled by `APPFLOWY_RATE_LIMIT_*` env vars; set
  `APPFLOWY_RATE_LIMIT_ENABLED=false` to disable.  Dry-run operations that
  make no network call do not consume rate budget.  Raises `AppFlowyError`
  when a bucket is exhausted (no silent retry/sleep).

- **MCP tool annotations hardened**: all 74 tool decorators now use explicit
  `ToolAnnotations` objects (no more dict type-ignore casts). Added
  `destructiveHint=True` for delete/trash/unpublish/delete-blob tools,
  `openWorldHint=True` for publish/upload/create/instantiate tools, and
  `idempotentHint=True` for read tools. Protocol-level error tests confirm
  FastMCP wraps `AppFlowyError` as `ToolError` at the tool boundary.

- **compact() truncation fix**: when output exceeds `max_chars`, `compact()`
  now returns a valid JSON object with `truncated: true`, `max_chars`,
  `original_chars`, a `preview` string, and `guidance` — never a raw
  cut JSON substring. Existing callers and MCP tools are unaffected for
  payloads within the limit.

### Added

- **`duplicate_published_page` / `instantiate_template`** …(previous entry)…

- **`append_markdown_to_page`** client method, `append-page-markdown` CLI command,
  and `appflowy_append_markdown_to_page` MCP tool.
  Converts a safe Markdown subset to AppFlowy SerdeBlocks (paragraphs, headings
  level 1–6, bulleted lists, numbered lists, blockquotes) and appends them to
  an existing page via `POST /api/workspace/{workspace_id}/page-view/{view_id}/append-block`.
  Block types confirmed from AppFlowy-Cloud upstream workspace-template fixture files.
  Dry-run by default; live execution requires `APPFLOWY_ALLOW_WRITES=true`.
  Does NOT fetch, replace, or perform block-level editing (fetch/replace/block edit
  remains backlog).  Unit-tested; no browser/human validation yet.
  Inline rich formatting (bold, italic, code span, links) is kept as plain text;
  full inline conversion is backlog.

- `src/appflowy_mcp_toolkit/markdown.py` — new internal `markdown_to_blocks` converter.
- `AppFlowyConfig.allow_publish_writes` and `_require_publish_writes_enabled` (from
  previous slice).
  Routes confirmed in AppFlowy-Cloud `src/api/workspace.rs`:
  `POST /api/workspace/{workspace_id}/page-view/{view_id}/publish` and `/unpublish`.
  Both operations are dry-run by default and require two explicit env gates for live
  execution: `APPFLOWY_ALLOW_WRITES=true` **and** `APPFLOWY_ALLOW_PUBLISH_WRITES=true`.
  Unit-tested; no browser/human validation yet.
- `AppFlowyConfig.allow_publish_writes` field (read from `APPFLOWY_ALLOW_PUBLISH_WRITES`).
- `AppFlowyClient._require_publish_writes_enabled()` helper that enforces both gates.

---

## [0.1.0] - 2026-05-18

First public PyPI release.

### Added

- **MCP server** (`appflowy-mcp-server`): stdio MCP server with read and opt-in
  write tools for workspaces, folders, databases, tasks, quick notes, search, and
  file storage.
- **CLI** (`appflowy-toolkit`): commands for all implemented REST/collab paths.
- **`appflowy-toolkit doctor`**: offline-safe install and environment check; reports
  package version, Python runtime, env flag presence (token masked to boolean),
  collab helper setup, MCP import availability, and recommended next steps.
  `--network` flag optionally calls the AppFlowy health endpoint.
- **Safe workflow guide**: `appflowy-toolkit workflows` and
  `appflowy_safe_workflows` expose the preferred task/card/page paths for agents
  without requiring credentials or network access.
- **`appflowy-toolkit setup-check`**: local Yjs/Node collab helper diagnostics
  (unchanged from pre-release; preserved for backward compatibility).
- **Task workflow**: `create_task`, `update_task`, `move_task`, `delete_task` and
  by-name / by-id variants. `create_task` uses AppFlowy's normal row-create route
  (browser-verified; `pre_hash` upsert route preserved for idempotent agent tasks).
- **Typed database fields**: select, multi-select, number, checkbox, URL, summary,
  time, datetime, and media cell writes with `create_typed_database_row_verified`.
- **File storage**: v1 upload/download/delete, usage/metadata reads, and a
  `upload_file_as_media` helper that returns a typed Media-cell object.
- **Collab write tools** (supported with explicit opt-in flags):
  row update by id, row delete, row reorder, board column reorder.
- **Self-hosted Docker test workflow** with seeded credentials and offline unit suite.
- **Browser smoke tests** (opt-in, Playwright): Grid rendering, task lifecycle,
  typed field rendering, Board visibility after Grid warm-up.
- **Validation evidence docs**: README and coverage matrix now distinguish
  unit-tested, self-hosted/Docker-tested, browser-tested, and human-verified
  support claims.
- **Template discovery**: read-only template-center tools for categories,
  creators, template listings, single template details, and template homepage groups.
- **Publishing metadata**: read-only tools for workspace publish namespace,
  default published view, published-page list, and per-view publish info.

### Known limitations / backlog

- Polished document/page Markdown editing is not supported. Page/view organization
  exists; document body editing is limited to low-level `append_blocks` and is
  tracked as backlog.
- Board rendering in AppFlowy Web can be stale after direct navigation. The
  established warm-up workaround (navigate > Grid tab > Board tab) is documented
  and used in browser tests.
- Row/card delete and reorder use Yjs collab mutations (no REST endpoint available
  in AppFlowy). These paths are tested but require explicit
  `APPFLOWY_ALLOW_COLLAB_WRITES=true` and a local Node.js runtime.
- Publish/unpublish writes, member/invite/admin mutations, AI/chat routes, and
  Notion migration are deferred.
- Template instantiation is not supported; AppFlowy's template-center routes are
  read-only for this release.
