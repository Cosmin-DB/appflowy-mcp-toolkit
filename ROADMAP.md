# Roadmap

## M0 — local repo foundation

- [x] README, DESIGN, ROADMAP, coordination notes.
- [x] Package skeleton.
- [x] Generic env example.
- [x] Research reports.

## M1 — read-only client/services

- [x] Config/env loading.
- [x] HTTP client with bearer auth and optional refresh retry.
- [x] AppFlowy error normalization.
- [x] Workspaces, folder, databases, fields, rows, row details.
- [x] Offline tests with mocked HTTP.

## M2 — CLI inspection

- [x] CLI entrypoint.
- [x] JSON output for core read commands.
- [ ] Manual smoke against real AppFlowy account.

## M3 — MCP read-only server

- [x] FastMCP entrypoint.
- [x] Read-only tools.
- [ ] In-process MCP tests if practical.
- [ ] Manual client smoke.

## M4 — public cleanup

- [ ] Secret scan.
- [ ] Remove private paths/IDs.
- [ ] Review docs for genericity.
- [ ] Decide license.
- [ ] Create public GitHub repo.

## M5 — safe writes later

- [x] Explicit write-enable flag.
- [x] Dry-run create/upsert row.
- [x] Post-write verification in local disposable workspace smoke test.
- [x] Disposable write integration smoke test.
