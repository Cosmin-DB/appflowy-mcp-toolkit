# Design

The toolkit is intentionally small and layered.

```text
AppFlowy REST API
  ↑
HTTP client + auth + errors
  ↑
Domain services: workspaces, folders, databases, rows
  ↑                 ↑
CLI inspection      MCP read-only tools
```

## Principles

- Read-only first.
- Explicit IDs over magic defaults.
- Treat AppFlowy IDs as opaque strings.
- Keep public repo generic; private workflows live outside it.
- No secrets in repo, logs, fixtures, or test output.
- Prefer boring Python over clever abstractions.

## Auth

The initial client uses bearer tokens from environment variables. Refresh-token support is implemented in the HTTP layer when `APPFLOWY_REFRESH_TOKEN` is present, but no token is written back to disk by default.

## Safety

Write tools are not part of the first milestone. Future writes must be explicitly enabled, schema-validated, dry-run capable, and tested against disposable data only.
