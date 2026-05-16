#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPSTREAM_DIR="${APPFLOWY_CLOUD_DIR:-$ROOT_DIR/.local/appflowy-cloud-test}"
UPSTREAM_REPO="${APPFLOWY_CLOUD_REPO:-https://github.com/AppFlowy-IO/AppFlowy-Cloud.git}"
UPSTREAM_REF="${APPFLOWY_CLOUD_REF:-0.9.64}"
UPSTREAM_SHA="${APPFLOWY_CLOUD_SHA:-ecf8c031d3c955508a0d3887acd61d970022db79}"
ENV_OVERRIDES="$ROOT_DIR/docker/appflowy-test/env.test.example"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required for the self-hosted AppFlowy test stack." >&2
  exit 127
fi

docker_cmd=(docker)
if ! docker ps >/dev/null 2>&1; then
  if sudo -n docker ps >/dev/null 2>&1; then
    docker_cmd=(sudo docker)
  else
    echo "Docker is installed but the current user cannot access the Docker daemon." >&2
    echo "Add the user to the docker group, or run 'sudo -v' before this script." >&2
    exit 126
  fi
fi

if ! "${docker_cmd[@]}" compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 is required: docker compose version failed." >&2
  exit 127
fi

mkdir -p "$(dirname "$UPSTREAM_DIR")"
if [ ! -d "$UPSTREAM_DIR/.git" ]; then
  git clone --depth 1 --branch "$UPSTREAM_REF" "$UPSTREAM_REPO" "$UPSTREAM_DIR"
else
  git -C "$UPSTREAM_DIR" fetch --depth 1 origin "refs/tags/$UPSTREAM_REF:refs/tags/$UPSTREAM_REF"
  git -C "$UPSTREAM_DIR" checkout "$UPSTREAM_REF"
fi

actual_sha="$(git -C "$UPSTREAM_DIR" rev-parse HEAD)"
if [ "$actual_sha" != "$UPSTREAM_SHA" ]; then
  echo "Unexpected AppFlowy-Cloud revision: $actual_sha (expected $UPSTREAM_SHA)." >&2
  exit 1
fi

cp "$UPSTREAM_DIR/deploy.env" "$UPSTREAM_DIR/.env"
{
  echo ""
  echo "# AppFlowy MCP test overrides"
  cat "$ENV_OVERRIDES"
} >> "$UPSTREAM_DIR/.env"

echo "Starting AppFlowy self-hosted stack from $UPSTREAM_DIR"
"${docker_cmd[@]}" compose --project-name appflowy-mcp-test --env-file "$UPSTREAM_DIR/.env" \
  -f "$UPSTREAM_DIR/docker-compose.yml" \
  -f "$ROOT_DIR/docker/appflowy-test/compose.override.yml" up -d

echo "Waiting for AppFlowy health endpoint..."
for _ in $(seq 1 90); do
  if curl -fsS http://localhost/health >/dev/null 2>&1 || curl -fsS http://localhost/api/health >/dev/null 2>&1; then
    echo "AppFlowy self-hosted stack is responding."
    exit 0
  fi
  sleep 2
done

echo "Timed out waiting for AppFlowy health. Inspect with:" >&2
echo "docker compose --project-name appflowy-mcp-test --env-file '$UPSTREAM_DIR/.env' -f '$UPSTREAM_DIR/docker-compose.yml' logs --tail=200" >&2
exit 1
