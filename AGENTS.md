# Agent working rules for this repo

This repo is intended for multi-agent work.

## Coordination

- The coordinator owns scope, review, and final integration.
- Worker agents receive narrow tasks and should touch only their assigned files.
- Every worker must report what changed, tests run, and remaining risks.

## Safety

- Never read or commit real secrets.
- Never commit `.env`, tokens, cookies, magic links, OTPs, personal emails, real workspace IDs, or local dumps.
- Public examples must use fake IDs such as `ws_demo_001`.

## Scope

Current accepted scope is broader than the original read-only draft:

- Read-only tools are safe to extend when routes are stable.
- Task-facing writes, page/view writes, quick-note writes, and selected destructive
  local/disposable operations exist, but must remain dry-run by default and guarded by
  explicit env flags.
- Docker is intentionally present only for optional self-hosted testing under
  `docker/appflowy-test/`; normal users do not need Docker to run read-only tools.
- Do not add publishing, sharing, invites, member/admin mutations, imports, AI/chat,
  account deletion, or broad file upload/delete without a separate safety design.
- Prefer small tested modules over framework-heavy abstractions.

## Agent Start Here

1. Read `README.md` for user-facing usage and known limitations.
2. Read `docs/appflowy-coverage-matrix.md` before adding new AppFlowy surface area.
3. Read `docs/browser-ui-acceptance.md` before interpreting web/Board rendering.
4. Use the self-hosted Docker stack for destructive tests; never use a private
   production workspace for write tests.
5. Keep browser-rendering evidence separate from API/collab data-plane truth.

## Review checklist

- Offline tests pass: `uv run pytest -q`.
- Lint/typecheck pass: `uv run ruff format --check .`, `uv run ruff check .`,
  `uv run mypy src tests`.
- Relevant opt-in live/self-hosted/browser tests pass or are explicitly xfailed with
  a documented reason.
- No secrets/private data.
- CLI/MCP behavior is generic.
- Errors are useful and redacted.
- No copied code from unlicensed/AGPL/license-conflicted repos.
