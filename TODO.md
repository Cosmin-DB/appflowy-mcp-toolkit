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
- Add row/card reordering inside a board column, with a narrow Yjs mutation and
  Docker/browser proof.
- Add board column reordering, again only after local Yjs/browser proof.
- Keep task operations explicit. Search may return exact/contains matches, but
  the calling AI must choose among candidates unless exactly one match exists.

## View Organization

- Keep view-configs read-only as the default diagnostic tool.
- Consider narrow mutations for common view settings only after Docker proof:
  field visibility, field width/wrap, simple sort, simple filter.
- Avoid implementing a generic edit-any-view-JSON tool. That would be too easy
  to misuse and would make the MCP responsible for AppFlowy's internal model.

## Page / Document Workflows

These are useful for people who use AppFlowy as a document workspace, but they
are not required for the current task-board use case.

- Add optional AI-friendly wrappers over the existing raw append-block route:
  append paragraph, heading, bullet list, numbered list, checklist, quote, and
  divider.
- Add page read helpers that summarize a page into plain text or markdown-like
  structure for an AI agent.
- Defer deep document editing: update block, delete block, move block, convert
  block type, and arbitrary Yjs document transactions. These need separate
  collab research and browser proof.

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

