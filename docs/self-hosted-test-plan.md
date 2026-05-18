# Self-Hosted Test Environment Plan

Goal: provide a reproducible local AppFlowy environment that can run destructive MCP
integration tests without touching AppFlowy official cloud or real workspaces.

This plan now has a validated initial implementation: `docker/appflowy-test/`,
`scripts/appflowy_test_env_up.sh`, `scripts/appflowy_test_env_down.sh`,
`scripts/appflowy_test_seed.py`, and `tests/selfhosted/`.

## Goal

A contributor should be able to run one documented flow:

1. Start a local AppFlowy stack.
2. Create or seed a disposable test user/workspace/database.
3. Point the MCP test suite at that local stack.
4. Run destructive task lifecycle tests.
5. Tear everything down and delete volumes.

The result should prove that the MCP works against a realistic AppFlowy deployment, not
only mocked HTTP.

## Official Sources To Use

Primary upstream source:

- Repository: `AppFlowy-IO/AppFlowy-Cloud`
- Compose file: `docker-compose.yml`
- Environment template: `deploy.env`
- Official deployment docs:
  - `https://docs.appflowy.io/docs/documentation/appflowy-cloud/deployment`
  - `https://github.com/AppFlowy-IO/AppFlowy-Cloud/blob/main/doc/DEPLOYMENT.md`

Important upstream facts observed on 2026-05-16:

- Official docs say self-hosting can run on one machine with Docker.
- Official routing through nginx:
  - `/gotrue` -> GoTrue auth
  - `/api` -> AppFlowy Cloud HTTP
  - `/ws` -> AppFlowy Cloud websocket
  - `/web` -> admin frontend
  - `/minio` -> MinIO UI
- Official compose includes at least:
  - `nginx`
  - `postgres` using `pgvector/pgvector:pg16`
  - `redis`
  - `minio`
  - `gotrue`
  - `appflowy_cloud`
  - `appflowy_web`
  - `appflowy_worker`
  - `appflowy_search`
  - optional/admin/AI services
- `deploy.env` contains local-friendly defaults:
  - `FQDN=localhost`
  - `SCHEME=http`
  - `WS_SCHEME=ws`
  - `APPFLOWY_BASE_URL=http://localhost`
  - `APPFLOWY_WEBSOCKET_BASE_URL=ws://localhost/ws/v2`
  - `GOTRUE_ADMIN_EMAIL=admin@example.com`
  - `GOTRUE_ADMIN_PASSWORD=password`
  - `GOTRUE_MAILER_AUTOCONFIRM=true`
  - `GOTRUE_DISABLE_SIGNUP=false`
  - `APPFLOWY_S3_USE_MINIO=true`
  - `APPFLOWY_S3_CREATE_BUCKET=true`

## Key Design Decisions

### Do Not Vendor AppFlowy

Do not copy a full AppFlowy source tree into this MCP repo.

Implemented structure:

```text
docker/appflowy-test/
  README.md
  compose.override.yml        # only MCP-specific overrides if needed
  env.test.example
scripts/
  appflowy_test_env_up.sh
  appflowy_test_env_down.sh
  appflowy_test_seed.py
tests/selfhosted/
  test_task_lifecycle.py
```

The test environment downloads the official AppFlowy-Cloud compose files at a pinned
revision into `.local/`. It does not vendor AppFlowy source into this repo.

### Pin Versions

The committed testing flow does not rely on `latest`.

Current pin:

- AppFlowy-Cloud tag `0.9.64`
- Commit `ecf8c031d3c955508a0d3887acd61d970022db79`
- Docker images:
  - `appflowy_cloud` / `appflowy_worker` / `gotrue` / `admin_frontend` `0.15.17`
  - `appflowy_web` `0.13.3`
  - `appflowy_ai` `0.15.10`

### Keep It Optional

Normal MCP users should not need Docker.

Default gates remain:

```bash
uv run ruff format .
uv run ruff check .
uv run mypy src
uv run pytest -q
```

Self-hosted tests are opt-in:

```bash
APPFLOWY_SELFHOSTED_TESTS=true uv run pytest tests/selfhosted -q
```

### Keep It Destructive But Isolated

Self-hosted tests may create/delete workspaces, pages, databases, fields, rows, and
documents because the environment is disposable.

The scripts must make this explicit and provide teardown/reset:

```bash
scripts/appflowy_test_env_down.sh --volumes
```

Never point self-hosted destructive tests at AppFlowy official cloud.

## Implementation Phases

### Phase D1 - Discovery Spike — done

Purpose: prove the upstream stack can start locally and expose the same API surface the MCP uses.

Tasks:

1. Fetch or checkout `AppFlowy-IO/AppFlowy-Cloud` at a recorded commit.
2. Copy `deploy.env` to a test env file.
3. Set deterministic local test values:
   - non-production JWT secret
   - test admin email/password
   - MinIO defaults
   - signup enabled/autoconfirm enabled
   - AI disabled unless required
4. Start the smallest viable compose profile.
5. Verify health:
   - `GET http://localhost/api/health`
   - GoTrue health if exposed
   - Web page loads if browser tests need it
6. Record required services and services that can be disabled.

Stop conditions:

- If official compose requires commercial/private images for the needed API.
- If AppFlowy Web/API cannot run without a license gate.
- If local auth cannot produce an access token non-interactively.
- If Docker resource usage is too high for a practical contributor flow.

### Phase D2 - Auth and Seed — done

Purpose: create repeatable test credentials and discover a test board.

Tasks:

1. Determine the correct GoTrue signup/login endpoint for local stack.
2. Create or login test user.
3. Capture access/refresh token for MCP tests.
4. Create a test workspace and database/board, either:
   - through existing MCP/API paths if possible, or
   - through a small seed script that uses official endpoints/browser automation.
5. Emit a local env file for tests:
   - `APPFLOWY_BASE_URL=http://localhost`
   - `APPFLOWY_ACCESS_TOKEN=...`
   - `APPFLOWY_REFRESH_TOKEN=...`
   - `APPFLOWY_TEST_WORKSPACE_ID=...`
   - `APPFLOWY_TEST_DATABASE_ID=...`
   - write gates enabled only for this test env.

Stop conditions:

- If board/database creation has no safe API and requires heavy UI automation, decide
  whether to seed through browser or pause and implement page/database tools first.

### Phase D3 - Self-Hosted Data-Plane Tests — done

Purpose: run the same task lifecycle smoke against local AppFlowy.

Tasks:

1. Run create -> update/move -> delete against the local Docker stack.
2. Keep the lifecycle self-contained; do not require AppFlowy official cloud.
3. Verify:
   - REST row list
   - REST row detail
   - database `row_orders`
   - DatabaseRow collab
   - delete removes row from view row lists
4. Keep these tests opt-in and destructive.

### Phase D4 - Browser/UI Acceptance — implemented as opt-in smoke

Purpose: verify user-visible behavior separately from data-plane correctness.

Current implementation:

- `tests/browser/test_appflowy_web_smoke.py` logs into the local AppFlowy Web stack.
- One test proves To-dos/Grid rendering.
- One test creates a row through the MCP/client, verifies REST/collab/blob-diff first,
  then requires AppFlowy Web Grid to render the verified row text.

Remaining browser-quality work:

1. Open local AppFlowy Web with Playwright/OpenClaw browser.
2. Navigate to the seeded board.
3. Record:
   - direct Board load behavior
   - Grid warm-up behavior
   - Board after Grid behavior
   - refresh/F5 behavior
4. Document whether the official Board/Grid cache bug reproduces locally.

This does not block data-plane tests unless the UI bug indicates actual data loss.

### Phase D5 - Contributor Workflow — partial

Purpose: make it usable by the community.

Deliverables:

- `docker/appflowy-test/README.md`
- `scripts/appflowy_test_env_up.sh`
- `scripts/appflowy_test_env_down.sh`
- `scripts/appflowy_test_seed.py`
- `tests/selfhosted/README.md`
- README section explaining:
  - normal tests
  - local self-hosted tests
  - self-hosted Docker tests
  - expected runtime/resources
  - cleanup command

## Open Questions / Remaining Work

- Can AI/admin/search services be disabled further for MCP task lifecycle tests without
  destabilizing the upstream compose stack?
- Seed is currently API-driven enough for the task lifecycle: it signs up/logs in through
  local GoTrue, verifies the local user, then discovers a workspace/database with the
  expected AppFlowy template fields. It does not yet create a board/database from scratch.
- Local auth currently works through GoTrue signup/login plus explicit local verification.
- The self-hosted stack exposes the AppFlowy API/collab surfaces needed by the current
  task lifecycle test; exact parity with AppFlowy official cloud is not exhaustively
  proven.
- The browser smoke now treats missing Grid rendering as a UI regression. Board rendering
  can still be stale after direct load, so Board screenshots remain diagnostic evidence
  rather than a release gate.

## Current Implementation Status

The repo contains a validated self-hosted test workflow. Latest verified battery:

- Docker compose services up.
- `GET /api/health` OK.
- AppFlowy Web redirects to `/app`.
- Seed reuse OK after the local one-seat license behavior was fixed.
- Self-hosted integration tests: 9 passed.
- Browser smoke: login/Grid passes; the MCP-created row rendering test must render in
  Grid. Board may still be stale depending on AppFlowy Web cache/rendering state.
- Offline unit pytest: 122 passed.
- Ruff format/check, mypy, build, and diff check passed.

Run the workflow with:

```bash
scripts/appflowy_test_env_up.sh
python scripts/appflowy_test_seed.py
set -a
source .env.selfhosted.generated
set +a
APPFLOWY_SELFHOSTED_TESTS=true uv run pytest tests/selfhosted -q
```

Run browser smoke with:

```bash
set -a
source .env.selfhosted.generated
set +a
APPFLOWY_BROWSER_TESTS=true uv run --extra browser pytest tests/browser -q -s
```
