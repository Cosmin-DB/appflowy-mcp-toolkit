#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPSTREAM_DIR="${APPFLOWY_CLOUD_DIR:-$ROOT_DIR/.local/appflowy-cloud-test}"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required to stop the self-hosted AppFlowy test stack." >&2
  exit 127
fi

args=(down)
if [ "${1:-}" = "--volumes" ]; then
  args+=(--volumes)
fi

docker compose --project-name appflowy-mcp-test --env-file "$UPSTREAM_DIR/.env" \
  -f "$UPSTREAM_DIR/docker-compose.yml" \
  -f "$ROOT_DIR/docker/appflowy-test/compose.override.yml" "${args[@]}"
