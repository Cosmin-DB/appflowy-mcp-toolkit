# Self-Hosted Test Environment Plan

Goal: provide a reproducible local AppFlowy environment that can run destructive MCP
integration tests without touching AppFlowy official cloud or Cosmin's real workspaces.

This plan now has an initial implementation: `docker/appflowy-test/`,
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

Preferred structure:

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

The test environment should either:

- clone/download the official AppFlowy-Cloud compose files at a pinned revision into a
  cache/temp directory, or
- document that the contributor must provide `APPFLOWY_CLOUD_DIR` pointing at a checked
  out `AppFlowy-Cloud` repo.

For reliability, prefer the first approach once proven.

### Pin Versions

Do not rely on `latest` in the final committed testing flow.

Initial spike may use upstream defaults to learn the stack, but the documented version
must pin one of:

- a specific AppFlowy-Cloud git commit + image tags, or
- explicit Docker image versions for `appflowy_cloud`, `appflowy_web`, `gotrue`,
  `appflowy_worker`, and related services.

If upstream does not publish stable tags suitable for this, pause and document the
versioning problem before implementing more tests.

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

### Phase D1 - Discovery Spike

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

### Phase D2 - Auth and Seed

Purpose: create repeatable test credentials and a test board.

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
   - `APPFLOWY_LIVE_WORKSPACE_ID=...`
   - `APPFLOWY_LIVE_DATABASE_ID=...`
   - write gates enabled only for this test env.

Stop conditions:

- If board/database creation has no safe API and requires heavy UI automation, decide
  whether to seed through browser or pause and implement page/database tools first.

### Phase D3 - Self-Hosted Data-Plane Tests

Purpose: run the same task lifecycle smoke against local AppFlowy.

Tasks:

1. Reuse/adapt `tests/live/test_task_lifecycle.py`.
2. Run create -> update/move -> delete.
3. Verify:
   - REST row list
   - REST row detail
   - database `row_orders`
   - DatabaseRow collab
   - delete removes row from view row lists
4. Keep these tests opt-in and destructive.

### Phase D4 - Browser/UI Acceptance

Purpose: verify user-visible behavior separately from data-plane correctness.

Tasks:

1. Open local AppFlowy Web with Playwright/OpenClaw browser.
2. Navigate to the seeded board.
3. Record:
   - direct Board load behavior
   - Grid warm-up behavior
   - Board after Grid behavior
   - refresh/F5 behavior
4. Document whether the official Board/Grid cache bug reproduces locally.

This should not block data-plane tests unless the UI bug indicates actual data loss.

### Phase D5 - Contributor Workflow

Purpose: make it usable by the community.

Deliverables:

- `docker/appflowy-test/README.md`
- `scripts/appflowy_test_env_up.sh`
- `scripts/appflowy_test_env_down.sh`
- `scripts/appflowy_test_seed.py`
- `tests/selfhosted/README.md`
- README section explaining:
  - normal tests
  - official live tests
  - self-hosted Docker tests
  - expected runtime/resources
  - cleanup command

## Open Questions

- Initial source pin selected: AppFlowy-Cloud tag `0.9.64`,
  commit `ecf8c031d3c955508a0d3887acd61d970022db79`.
- Initial Docker image pins selected from published Docker Hub tags:
  `appflowy_cloud`/`appflowy_worker`/`gotrue`/`admin_frontend` `0.15.17`,
  `appflowy_web` `0.13.3`, and `appflowy_ai` `0.15.10`.
- Can AI/admin/search services be disabled for MCP task lifecycle tests?
- Is AppFlowy Web required for seed, or can seed be fully API-driven?
- What is the most reliable non-interactive auth flow for GoTrue in this stack?
- Does the self-hosted stack expose exactly the same `/api/workspace/...` endpoints
  as AppFlowy official cloud?
- Does the Board/Grid refresh bug reproduce in self-hosted `appflowy_web`?

## Current Implementation Status

The MCP-side checklist in `docs/execution-roadmap.md` is complete. The repo now contains
the first self-hosted test workflow scaffold. It cannot be validated on a machine without
Docker; when Docker is available, the next verification step is:

```bash
scripts/appflowy_test_env_up.sh
python scripts/appflowy_test_seed.py
set -a
source .env.selfhosted.generated
set +a
APPFLOWY_SELFHOSTED_TESTS=true uv run pytest tests/selfhosted -q
```
