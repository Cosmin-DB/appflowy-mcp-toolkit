# Changelog

All notable changes to `appflowy-mcp-toolkit` are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Added

- **`publish_page` / `unpublish_page`** client methods, `publish-page` / `unpublish-page`
  CLI commands, and `appflowy_publish_page` / `appflowy_unpublish_page` MCP tools.
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
