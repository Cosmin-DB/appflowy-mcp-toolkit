# Release Checklist

This repo is a pre-1.0 release candidate. Use this checklist before publishing or
handing the project to external contributors.

## Scope

Included:

- AppFlowy REST client, CLI, and MCP server.
- Read coverage for server/user/workspace/folder/page/database/row/search/file metadata.
- Guarded writes for task rows, page/view organization, fields, quick notes, and trash flows.
- Experimental Yjs row delete behind explicit write + collab write gates.
- Optional self-hosted Docker and browser smoke tests.

Deferred:

- Publishing/sharing/invites/member/admin mutations.
- Imports and AI/chat routes.
- Broad file upload/download/delete.
- Account/workspace destructive administration.
- Full AppFlowy Web visual parity for MCP-created rows.

## Required Gates

Run from a clean checkout or clean worktree:

```bash
uv run pytest -q
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv build
git diff --check
```

Optional but expected before public release when local Docker is available:

```bash
scripts/appflowy_test_env_up.sh
python scripts/appflowy_test_seed.py
set -a
source .env.selfhosted.generated
set +a
APPFLOWY_SELFHOSTED_TESTS=true uv run pytest tests/selfhosted -q -s
APPFLOWY_BROWSER_TESTS=true uv run --extra browser pytest tests/browser -q -s
```

Current expected browser result: one Grid/login smoke passes and one MCP-created-row
rendering observation is `xfail` if AppFlowy Web does not render the row despite
REST/collab/blob-diff verification passing.

## Safety Review

Before publishing:

- Confirm `git status --short` is clean.
- Confirm `.env`, `.env.*`, `.local/`, caches, virtualenvs, generated screenshots, and
  generated test credentials are ignored.
- Scan tracked files for tokens, private workspace IDs, real emails, local dumps, and
  personal paths.
- Keep examples generic and fake.
- Keep write tools dry-run by default.
- Keep destructive tests opt-in and explicitly disposable.

## Documentation Review

A new contributor or AI agent should be able to start from:

- `README.md` for installation, CLI/MCP usage, and known limitations.
- `AGENTS.md` for agent rules and test expectations.
- `docs/appflowy-coverage-matrix.md` for implemented/deferred AppFlowy surface.
- `docs/self-hosted-test-plan.md` for local Docker testing.
- `docs/browser-ui-acceptance.md` for browser/UI caveats.
