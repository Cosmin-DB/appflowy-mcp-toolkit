# TODO

This project should stay a toolkit for agents, not a second AppFlowy web client.
The MCP should expose clear, bounded operations and return enough state for the
calling AI to decide what to do. It should not guess user intent or hide
ambiguous choices behind heuristics.

## Near-Term Task Workflows

- Add browser acceptance for board column operations against local Docker:
  create, rename, hide, show, refresh, switch Grid/Board, and assert no web
  console/runtime error.
- Implement safe Status option deletion only after Docker proves the policy for
  rows that still reference the deleted option. Likely choices: reject when used,
  or require an explicit replacement Status.
- [DONE] Add row/card reordering inside a board column, with a narrow Yjs mutation.
  Docker/browser proof still pending; unit tests and offline Yjs helper integration tests cover the mutation behavior.
- [DONE] Add board column reordering via Yjs childGroups mutation.
  Docker/browser proof still pending; unit tests and offline Yjs helper integration tests cover the mutation behavior.
- Keep task operations explicit. Search may return exact/contains matches, but
  the calling AI must choose among candidates unless exactly one match exists.

## MCP Hardening Before Next Release

These items came from an external MCP review and local code inspection. Treat
the first item as release-blocking for a calm public release; the rest are
ordered by practical risk and protocol maturity.

- [P0] Harden local file uploads. The MCP upload path must not become a general
  local filesystem reader. Add an explicit local-read gate such as
  APPFLOWY_ALLOW_LOCAL_FILE_READS=true, require configured allowed roots such
  as APPFLOWY_ALLOWED_FILE_ROOTS, reject paths outside those roots, handle
  traversal/symlink cases, and make dry-run use metadata (stat) instead of
  read_bytes().
- [DONE] Stop returning invalid truncated JSON. compact() returns a valid JSON
  wrapper with truncated: true, the limit, original_chars, a preview string, and
  guidance when output exceeds max_chars.
- [DONE] Make raw collab diagnostics explicit and safer. get_collab_json now
  defaults to summary_only=True, include_raw=False for public CLI/MCP callers.
  Full raw output requires include_raw=True. Internal callers unchanged.
- [P1] Sweep docs for support-status drift before release. README,
  coverage matrix, release checklist, changelog, and tool docs must agree about
  templates, publishing, Markdown append support, and deferred page editing.
- [DONE] Add simple MCP/server-side rate limits: per-client sliding-window buckets
  for calls per minute, writes per minute, blob/collab per minute, and max
  concurrent calls. Controlled via APPFLOWY_RATE_LIMIT_* env vars;
  APPFLOWY_RATE_LIMIT_ENABLED=false disables. Raises AppFlowyError on excess.
- [DONE] Add richer MCP annotations: destructiveHint on delete/trash/unpublish/delete-blob,
  openWorldHint on publish/upload/create/instantiate, idempotentHint on read tools.
  All annotations now use ToolAnnotations objects (no more dict type-ignore casts).
- [DONE] Add protocol-level tool error tests. Verified that FastMCP wraps AppFlowyError
  as ToolError (not a protocol crash). Tests in test_mcp_annotations_errors.py.
- [P3] Consider structured MCP responses for high-value tools while preserving
  text/JSON compatibility for clients that expect the current shape.

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

- Current status: page/view organization exists, but document-body workflows are
  backlog. The existing raw append-block route is a low-level primitive, not a
  complete document editor.
- Add optional AI-friendly wrappers over the existing raw append-block route:
  append paragraph, heading, bullet list, numbered list, checklist, quote, and
  divider.
- Add page read helpers that summarize a page into plain text or markdown-like
  structure for an AI agent:
  - fetch_page_markdown
  - append_page_markdown
  - replace_page_markdown
- Defer deep document editing: update block, delete block, move block, convert
  block type, and arbitrary Yjs document transactions. These need separate
  collab research, unit fixtures over Yjs documents, self-hosted proof, and
  browser proof.

## Deferred Product Areas

Do not implement these casually:

- publishing and public sharing
- member, invite, access request, and admin workflows
- import/export workflows with external side effects
- AppFlowy AI/chat automation
- generic collab object mutation

These areas either affect other people, make data public, depend on product/AI
services, or require policy decisions beyond a normal task-board MCP.

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
