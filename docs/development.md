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
