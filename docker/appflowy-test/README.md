# AppFlowy Self-Hosted Test Stack

This directory defines the MCP project's optional self-hosted AppFlowy test workflow.
It does not vendor AppFlowy. Scripts fetch the official `AppFlowy-IO/AppFlowy-Cloud`
compose project at a pinned tag into `.local/`.

Current pin:

- Repository: `https://github.com/AppFlowy-IO/AppFlowy-Cloud.git`
- Ref: `0.9.64`
- Commit: `ecf8c031d3c955508a0d3887acd61d970022db79`
- Docker images:
  - `appflowyinc/appflowy_cloud:0.15.17`
  - `appflowyinc/appflowy_worker:0.15.17`
  - `appflowyinc/gotrue:0.15.17`
  - `appflowyinc/admin_frontend:0.15.17`
  - `appflowyinc/appflowy_web:0.13.3`
  - `appflowyinc/appflowy_ai:0.15.10`

## Requirements

- Docker with the Compose v2 plugin.
- Network access for the first upstream checkout and image pulls.
- Enough local resources for Postgres, Redis, MinIO, GoTrue, AppFlowy Cloud, worker, and
  AppFlowy Web.

Normal unit tests do not need Docker.

## Start

```bash
scripts/appflowy_test_env_up.sh
```

The script:

1. checks Docker availability;
2. checks out the pinned AppFlowy-Cloud revision under `.local/`;
3. creates a local `.env` from upstream `deploy.env`;
4. applies deterministic test overrides from `env.test.example`;
5. applies `compose.override.yml` for test-only service env fixes;
6. runs `docker compose up -d`.

## Seed/Auth

Once the stack is healthy:

```bash
python scripts/appflowy_test_seed.py
```

The seed script signs up or logs in a disposable local user through GoTrue, discovers or
creates a workspace, finds a database with `Description` and `Status` fields, and writes a
generated environment file for destructive MCP tests.

If the default AppFlowy templates change and no compatible database exists, the seed script
stops with a clear message instead of fabricating an unverified board shape.

## Test

```bash
set -a
source .env.selfhosted.generated
set +a
APPFLOWY_SELFHOSTED_TESTS=true uv run pytest tests/selfhosted -q
```

These tests are destructive but isolated to the local stack.

## Stop

```bash
scripts/appflowy_test_env_down.sh
scripts/appflowy_test_env_down.sh --volumes
```

The `--volumes` form deletes AppFlowy's local Docker volumes.

Never point self-hosted destructive tests at AppFlowy official cloud.
