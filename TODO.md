# TODO

This project should stay a toolkit for agents, not a second AppFlowy web client.
The MCP should expose clear, bounded operations and return enough state for the
calling AI to decide what to do. It should not guess user intent or hide
ambiguous choices behind heuristics.

## Near-Term Task Workflows

- [DONE] Add browser acceptance for board column operations against local Docker:
  create/ensure, rename, hide, show, refresh, and switch Grid/Board now have
  focused browser coverage in `tests/browser/test_appflowy_web_board_acceptance.py`.
- Implement safe Status option deletion only after Docker proves the policy for
  rows that still reference the deleted option. Likely choices: reject when used,
  or require an explicit replacement Status.
- [DONE] Add row/card reordering inside a board column, with a narrow Yjs mutation.
  Docker/browser proof still pending; unit tests and offline Yjs helper integration tests cover the mutation behavior.
- [DONE] Add board column reordering via Yjs childGroups mutation.
  Docker/browser proof now covers data-plane order plus Board presence; exact
  visual column order remains intentionally unasserted until AppFlowy Web exposes
  stable column positions.
- Keep task operations explicit. Search may return exact/contains matches, but
  the calling AI must choose among candidates unless exactly one match exists.

## MCP Hardening Before Next Release

These items came from an external MCP review and local code inspection. Treat
the first item as release-blocking for a calm public release; the rest are
ordered by practical risk and protocol maturity.

- [DONE] Harden local file uploads. APPFLOWY_ALLOW_LOCAL_FILE_READS and
  APPFLOWY_ALLOWED_FILE_ROOTS gates added; dry-run uses stat() only; path
  traversal and symlink escape rejected; upload_file_as_media also covered.
- [DONE] Stop returning invalid truncated JSON. compact() returns a valid JSON
  wrapper with truncated: true, the limit, original_chars, a preview string, and
  guidance when output exceeds max_chars.
- [DONE] Make raw collab diagnostics explicit and safer. get_collab_json now
  defaults to summary_only=True, include_raw=False for public CLI/MCP callers.
  Full raw output requires include_raw=True. Internal callers unchanged.
- [DONE] Sweep docs for support-status drift before release. README,
  coverage matrix, release checklist, changelog, and tool docs aligned
  for 0.1.0: templates, publishing, Markdown append, collab diagnostics,
  local upload hardening, and rate limiting all documented consistently.
- [DONE] Add simple MCP/server-side rate limits: per-client sliding-window buckets
  for calls per minute, writes per minute, blob/collab per minute, and max
  concurrent calls. Controlled via APPFLOWY_RATE_LIMIT_* env vars;
  APPFLOWY_RATE_LIMIT_ENABLED=false disables. Raises AppFlowyError on excess.
- [DONE] Add richer MCP annotations: destructiveHint on delete/trash/unpublish/delete-blob,
  openWorldHint on publish/upload/create/instantiate, idempotentHint on read tools.
  All annotations now use ToolAnnotations objects (no more dict type-ignore casts).
- [DONE] Add protocol-level tool error tests. Verified that FastMCP wraps AppFlowyError
  as ToolError (not a protocol crash). Tests in test_mcp_annotations_errors.py.
- [P0] Make the MCP server rate limiter shared per server process, not per
  short-lived `AppFlowyClient`, so limits apply across tool calls in the same
  MCP process. Keep client-level limits as a fallback, but enforce shared server
  buckets for real protocol usage.
- [P0] Add structured MCP responses (`structuredContent`) for high-value tools
  while preserving text/JSON compatibility for clients that expect the current
  shape. Start with: `list_tasks`, `get_database_rows`,
  `verify_database_row`, `create_task`, `publish_page`, `list_templates`, and
  `get_database_view_configs`.
- [P0] Add MCP error-handling tests for `AppFlowyError`, auth failures,
  rate-limit failures, write-gate failures, and local-file-read-gate failures.
  The server should return clean tool errors, not crash or leak traceback-shaped
  protocol responses.
- [P1] Strengthen public input validation: UUID-like ids where appropriate,
  max lengths for names/descriptions/publish slugs, enum validation for layouts,
  collab types, field/status operations, and pagination parameters.
- [P1] Improve pagination and explicit limits for large-output tools: rows,
  search, folder tree, templates, and collab diagnostics. Do not rely only on
  final-output truncation.
- [P1] Consolidate advanced/diagnostic tools behind clearer naming or explicit
  flags (`debug`, `advanced`, `include_raw`) so agents do not call broad or raw
  diagnostics by accident.

## View Organization

- Keep view-configs read-only as the default diagnostic tool.
- Consider narrow mutations for common view settings only after Docker proof:
  field visibility, field width/wrap, simple sort, simple filter.
- Avoid implementing a generic edit-any-view-JSON tool. That would be too easy
  to misuse and would make the MCP responsible for AppFlowy's internal model.

## Page / Document Workflows

These are useful for people who use AppFlowy as a document workspace, but they
are not required for the current task-board use case. Do not market the current
raw block route as polished page/Markdown editing support.

- Current status: page/view organization exists and `append_page_markdown` is
  supported, but full document-body workflows remain backlog. The existing raw
  append-block route is a low-level primitive, not a complete document editor.
- [P1] Add page read helpers that summarize a page into plain text or
  markdown-like structure for an AI agent:
  - fetch_page_markdown
- [P1] Add replace-page Markdown workflow only after safe round-trip tests:
  - replace_page_markdown
- [P2] Add optional AI-friendly wrappers over the existing raw append-block route:
  append paragraph, heading, bullet list, numbered list, checklist, quote, and
  divider.
- [P2] Defer deep document editing until there are fixtures and browser proof:
  update block, delete block, insert block, move block, convert
  block type, and arbitrary Yjs document transactions. These need separate
  collab research, unit fixtures over Yjs documents, self-hosted proof, and
  browser proof.

## Deferred Product Areas

Do not implement these casually:

- broad publishing and public sharing beyond the currently gated publish/unpublish
- member, invite, access request, and admin workflows
- import/export workflows with external side effects
- AppFlowy AI/chat automation
- generic collab object mutation

These areas either affect other people, make data public, depend on product/AI
services, or require policy decisions beyond a normal task-board MCP.

- [P1] Add a separate external-content gate, for example
  `APPFLOWY_ALLOW_EXTERNAL_CONTENT_IMPORTS=true`, before duplicating/importing
  content from outside the user's own trusted workspace. Apply it to
  `duplicate_published_page` / `instantiate_template` if the source provenance
  is not clearly local/trusted.
- [P1] Complete Quick Notes investigation. Current AppFlowy Cloud smoke showed
  create/update/delete return success, but `quick-notes` list remains empty.
  Do not call Quick Notes end-user-ready until the product/list behavior is
  understood and tested.
- [P2] Add targeted self-hosted/cloud smoke tests for publishing, templates,
  append Markdown, and Quick Notes where the deployment supports them. Keep
  data-plane assertions separate from browser/UI assertions.

## Design Rule

The MCP should provide tools, not replace the reasoning agent.

Good:
- list tasks
- search tasks by exact/contains Description
- return candidates when multiple rows match
- move this specific row to this explicit Status
- show a dry-run payload before a risky write

Avoid:
- find something similar and decide what I meant
- clean this board however you think
- silently choosing among duplicates
- broad mutation endpoints that accept internal AppFlowy JSON without guardrails
