# Release Checklist

This checklist covers the steps before publishing or handing the project to external
contributors. See `CHANGELOG.md` for what is included in each release.

## Scope

Included:

- AppFlowy REST client, CLI, and MCP server.
- Read coverage for server/user/workspace/folder/page/database/row/search/file metadata.
- Explicit opt-in writes for task rows, page/view organization, fields, quick notes,
  and trash flows.
- Gated publish/unpublish page writes (`APPFLOWY_ALLOW_WRITES` + `APPFLOWY_ALLOW_PUBLISH_WRITES`).
- Published template/page duplication into workspace (`duplicate-published-page`,
  `instantiate-template`); arbitrary unpublished template instantiation not supported.
- Template-center discovery reads (categories, creators, templates, homepage).
- Append Markdown to page (paragraphs, headings, lists, blockquotes). Full
  fetch/replace/block-level document editing remains backlog.
- Experimental Yjs row delete and ordering behind explicit write + collab write gates.
- Local file upload safety gates: `APPFLOWY_ALLOW_LOCAL_FILE_READS`,
  `APPFLOWY_ALLOWED_FILE_ROOTS`, path-traversal and symlink rejection.
- In-process rate limiting (`APPFLOWY_RATE_LIMIT_*`; default-on, conservative limits).
- Safe collab diagnostics: `get_collab_json` defaults to summary; raw requires
  `include_raw=True` / CLI `--include-raw` / `--full`.
- Valid JSON for truncated MCP outputs (no more cut JSON strings).
- Rich MCP annotations (`destructiveHint`, `openWorldHint`, `idempotentHint`).
- Optional self-hosted Docker and browser smoke tests.

Deferred:

- Member/invite/access/admin mutations.
- Imports, AI/chat, and broad administrative routes.
- Full AppFlowy Web visual parity for MCP-created rows.
- Full document fetch/replace/block-level editing.
- Self-hosted smoke tests for template-center (requires seeded data).

## Required Gates

Run from a clean checkout or clean worktree:

```bash
scripts/test_all_local.sh
```

This is the preferred local release battery. It is self-contained except for Docker,
uses the disposable self-hosted AppFlowy stack, and does not call AppFlowy official
cloud. If Docker requires elevated access on the host, run `sudo -v` first or add
the user to the Docker group.

The same gates can be run manually as:

```bash
uv run pytest tests/unit -q
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv build
git diff --check
```

Self-hosted and browser gates:

```bash
scripts/appflowy_test_env_up.sh
uv run python scripts/appflowy_test_seed.py
set -a
source .env.selfhosted.generated
set +a
APPFLOWY_SELFHOSTED_TESTS=true uv run pytest tests/selfhosted -q -s
APPFLOWY_BROWSER_TESTS=true uv run --extra browser pytest tests/browser -q -s
```

Current expected browser result: Grid/login smoke, task lifecycle, typed field
rendering, and Board visibility after Grid warm-up all pass. Board screenshots
remain diagnostic evidence for stale Board rendering. Row/card reorder
data-plane is unit-tested; Board visual ordering is pending browser proof.

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

## PyPI Publishing

The package is published with PyPI Trusted Publishing, not a long-lived API token.
Do not paste PyPI tokens into chat, issues, logs, or local files.

One-time PyPI setup:

- PyPI project name: `appflowy-mcp-toolkit`
- GitHub owner: `Cosmin-DB`
- GitHub repository: `appflowy-mcp-toolkit`
- Workflow filename: `release.yml`
- GitHub environment: `pypi`

Local package verification before creating a GitHub Release:

```bash
rm -rf dist
uv build
uv run --with twine python -m twine check dist/*
pipx install --force dist/*.whl
appflowy-toolkit doctor
appflowy-toolkit --help
appflowy-mcp-server --help
```

If `pipx` is not installed on the local machine, the same wheel can be checked with uv:

```bash
uv tool install --force dist/*.whl
appflowy-toolkit doctor
appflowy-toolkit --help
appflowy-mcp-server --help
```

Publish flow:

1. Confirm all release gates pass.
2. Confirm the PyPI Trusted Publisher above is configured.
3. Create and push a version tag, for example `v0.1.0`.
4. Create a GitHub Release from that tag.
5. The `release.yml` workflow builds the wheel/sdist and publishes to PyPI.
