# Development

Install locally:

```bash
python -m pip install -e '.[dev,mcp]'
```

Quality gates:

```bash
python -m pytest
python -m ruff format --check .
python -m ruff check .
python -m mypy src tests
```

## Architecture

The codebase is split by responsibility rather than by individual MCP tool:

- `client.py` owns transport concerns only: HTTP requests, auth refresh, response
  extraction, write gates, URL building, and the shared client configuration.
- `client_parts/` contains AppFlowy domain mixins. Each module groups API methods
  for one area such as pages, databases, tasks/rows, publishing, templates, files,
  diagnostics, or workspaces.
- `client_parts/base.py` is the internal typing contract shared by mixins. It
  avoids circular imports while making cross-domain calls explicit to `mypy`.
- `client_parts/helpers.py` contains private normalization helpers for AppFlowy
  collab/database shapes. Keep schema-shape compatibility code here unless it is
  specific to one domain.
- `mcp/server.py` owns MCP process setup: the FastMCP instance, shared
  process-level rate limiter, client construction, structured tool result helper,
  and server entrypoint.
- `mcp/tools/` contains MCP tool registrations grouped by public feature area.
  Tool names are the public API, so moving code between modules must not rename
  tools without an intentional compatibility decision.

When adding functionality, prefer this path:

1. Add or update AppFlowy API behavior in the relevant `client_parts/` module.
2. Expose it through the matching `mcp/tools/` module.
3. Add unit tests at the client/tool boundary before any live cloud or browser
   smoke test.
4. Keep risky writes behind the existing gates, or add a new explicit gate when
   the blast radius is meaningfully different.

Self-hosted Docker smoke:

```bash
scripts/appflowy_test_env_up.sh
python scripts/appflowy_test_seed.py
set -a
source .env.selfhosted.generated
set +a
APPFLOWY_SELFHOSTED_TESTS=true uv run pytest tests/selfhosted -q
```

Pre-release local battery:

```bash
uv run pytest -q
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv build
git diff --check
```

Browser/UI acceptance is tracked separately from API/collab truth. The local Docker
stack can be smoke-rendered at `http://localhost/app`; a full browser acceptance pass
should use Playwright or an allowed browser profile and follow
`docs/browser-ui-acceptance.md`.

Opt-in Playwright browser smoke:

```bash
set -a
source .env.selfhosted.generated
set +a
APPFLOWY_BROWSER_TESTS=true uv run --extra browser pytest tests/browser -q -s
```

For a release-style run that also enables the self-hosted suite:

```bash
APPFLOWY_BROWSER_TESTS=true APPFLOWY_SELFHOSTED_TESTS=true \
  uv run --extra browser pytest -q -rs
```

If Docker socket permissions depend on group membership that is not loaded in
the current shell, run the same command through `sg docker`.
