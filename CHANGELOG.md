# Changelog

All notable changes to `appflowy-mcp-toolkit` are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

No unreleased changes yet.

## [0.3.0] - 2026-05-18

MCP protocol hardening release. This release keeps the AppFlowy feature surface
from `0.2.0` and improves how agents consume results, share rate limits, and
recover from operational failures.

### Added

- **Structured MCP outputs** for high-value tools while preserving the existing
  text/JSON response for backwards compatibility:
  `appflowy_list_tasks`, `appflowy_get_database_rows`,
  `appflowy_verify_database_row`, `appflowy_create_task`,
  `appflowy_publish_page`, `appflowy_list_templates`, and
  `appflowy_get_database_view_configs`. List-like structured payloads are exposed
  as `{"result": [...]}` because MCP `structuredContent` must be a JSON object.
- **MCP error-handling coverage** for `AppFlowyError`, auth failures, rate-limit
  failures, write-gate failures, and local-file-read-gate failures. These cases
  are verified to surface as clean FastMCP tool errors instead of raw exceptions
  or traceback-shaped protocol responses.

### Changed / Hardened

- **MCP server rate limiting is now shared per server process**. Tool calls in the
  same MCP server consume the same limiter buckets, so agents cannot bypass the
  limit by creating a fresh `AppFlowyClient` per tool call. CLI/direct client usage
  keeps the existing per-client limiter fallback.

## [0.2.0] - 2026-05-18

Validated AppFlowy Cloud release with page publishing, template duplication, Markdown
append, browser acceptance coverage, and safety hardening.

### Added

- **`publish_page` / `unpublish_page`**: gated publish/unpublish writes for page
  views. Routes confirmed in AppFlowy-Cloud `src/api/workspace.rs`. Require
  `APPFLOWY_ALLOW_WRITES=true` **and** `APPFLOWY_ALLOW_PUBLISH_WRITES=true` for
  live execution. Dry-run by default. Unit-tested; public URL visibility is
  browser-tested against the local self-hosted stack.
- **`duplicate_published_page` / `instantiate_template`**: duplicates a published
  page or template into a workspace destination view. Route confirmed:
  `POST /api/workspace/{workspace_id}/published-duplicate`. Requires
  `APPFLOWY_ALLOW_WRITES=true` only. Unit-tested; published-page instantiation is
  browser-tested against the local self-hosted stack. Arbitrary unpublished template
  instantiation is not supported via this route.
- **`append_markdown_to_page`** client method, `append-page-markdown` CLI command,
  and `appflowy_append_markdown_to_page` MCP tool. Converts a safe Markdown subset
  (paragraphs, headings 1–6, bulleted/numbered lists, blockquotes) to AppFlowy
  SerdeBlocks and appends to an existing page. Block types confirmed from upstream
  workspace-template fixture files. Inline rich formatting is kept as plain text
  (backlog). Does NOT fetch, replace, or perform block-level editing. Unit-tested;
  visible appended content is browser-tested against the local self-hosted stack.
- **Template-center read-only discovery**: `list_template_categories`,
  `get_template_category`, `list_template_creators`, `get_template_creator`,
  `list_templates`, `get_template`, `get_template_homepage` — routes confirmed in
  AppFlowy-Cloud `src/api/template.rs`. Unit-tested.

### Changed / Hardened

- **Local file upload hardening**: `upload_local_file_blob_v1` and
  `upload_file_as_media` now require `APPFLOWY_ALLOW_LOCAL_FILE_READS=true` and a
  non-empty `APPFLOWY_ALLOWED_FILE_ROOTS` for both dry-run (stat only) and live
  execution. Path traversal and symlink escape are rejected via `resolve(strict=True)`.
- **Valid truncated JSON**: `compact()` now returns a valid JSON wrapper object when
  output exceeds `max_chars` (`truncated`, `max_chars`, `original_chars`, `preview`,
  `guidance`). No more raw cut JSON substrings.
- **Safer collab diagnostics**: `get_collab_json` defaults to `summary_only=True,
  include_raw=False` for CLI and MCP callers. Full raw output requires `--include-raw`
  / `--full` (CLI) or `include_raw=True, summary_only=False` (client/MCP). Internal
  callers (`get_database_row_orders` etc.) are unaffected.
- **In-process rate limiting**: `AppFlowyClient` enforces sliding-window buckets at
  the network layer. Defaults: 120 calls/min, 30 writes/min, 20 blob/collab/min,
  8 concurrent. Controlled by `APPFLOWY_RATE_LIMIT_*` env vars;
  `APPFLOWY_RATE_LIMIT_ENABLED=false` disables. Dry-run operations do not consume
  network rate budget. Raises `AppFlowyError` on excess (no silent retry).
- **Rich MCP annotations**: all tool decorators use `ToolAnnotations` objects with
  `destructiveHint` (delete/trash/unpublish tools), `openWorldHint`
  (publish/upload/create/instantiate), and `idempotentHint` (read tools). FastMCP
  wraps `AppFlowyError` as `ToolError` at the tool boundary (confirmed by tests).

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
- Arbitrary unpublished template instantiation is not supported; published page/template
  duplication is supported through AppFlowy's published-duplicate route.
