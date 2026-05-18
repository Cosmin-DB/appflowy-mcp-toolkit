# Changelog

All notable changes to `appflowy-mcp-toolkit` are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
- Member/invite/admin mutations, AI/chat routes, and Notion migration are deferred.
