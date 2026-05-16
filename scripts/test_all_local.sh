#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "== AppFlowy MCP local release battery =="
echo

echo "== 1/7 Offline unit pytest suite =="
uv run pytest tests/unit -q
echo

echo "== 2/7 Formatting check =="
uv run ruff format --check .
echo

echo "== 3/7 Lint =="
uv run ruff check .
echo

echo "== 4/7 Type check =="
uv run mypy src tests
echo

echo "== 5/7 Build =="
uv build
echo

echo "== 6/7 Self-hosted AppFlowy integration =="
scripts/appflowy_test_env_up.sh
uv run python scripts/appflowy_test_seed.py
set -a
# shellcheck disable=SC1091
source .env.selfhosted.generated
set +a
APPFLOWY_SELFHOSTED_TESTS=true uv run pytest tests/selfhosted -q -s
echo

echo "== 7/7 Browser smoke against self-hosted AppFlowy =="
APPFLOWY_BROWSER_TESTS=true uv run --extra browser pytest tests/browser -q -s
echo

echo "== Git whitespace check =="
git diff --check
echo

echo "Local release battery completed."
echo "Note: browser tests may report an expected xfail for AppFlowy Web rendering MCP-created rows."
