# Safety

This project is read-first, with opt-in write tools that are strictly guarded.

## Secrets

Never commit:

- `.env` files with real values;
- access or refresh tokens;
- cookies;
- OTPs or magic links;
- personal emails;
- real workspace/database/row IDs from a private account;
- raw API dumps from a real account.

## Writes

Write tools are available but **disabled by default**. They require explicit opt-in:

- All write tools default to `dry_run=True`; no mutation happens unless the caller
  passes `dry_run=False`.
- Real writes additionally require the environment variable `APPFLOWY_ALLOW_WRITES=true`.
  Without it, even `dry_run=False` calls raise an error.
- Post-write verification is performed where possible (e.g. `move_managed_task_status`
  fetches and returns the updated row after a real write).

## Experimental: Yjs-based row delete

`appflowy_delete_database_row` / `delete-row` CLI / `delete_database_row_collab()` are
experimental (M6.3). They require **two** opt-in flags:

- `APPFLOWY_ALLOW_WRITES=true`
- `APPFLOWY_ALLOW_COLLAB_WRITES=true`

They also require Node.js 18+ and the `yjs` npm package:

```bash
cd src/appflowy_mcp_toolkit/collab && npm install
```

This is the only confirmed-correct delete path (AppFlowy Web does not expose a REST
row-delete endpoint). The implementation has been live-tested against a disposable
official and self-hosted disposable workspaces as part of the task lifecycle, but it is
not recommended for production use. The current verification means removal from database
view row lists and REST row lists; explicit row-detail lookup by id may still return the
old row object on some AppFlowy deployments. All defaults are dry-run.

Row/card deletion in AppFlowy Web is handled by mutating the database collab/Yjs document
and syncing a binary update, not by a semantic REST delete endpoint. Future delete support
must therefore use a verified collab mutator, an explicit experimental opt-in, and
disposable-workspace proof before it is exposed as an MCP tool.

Future write tools must:

- be disabled by default;
- require explicit opt-in via `APPFLOWY_ALLOW_WRITES`;
- support dry-run previews where practical;
- validate target workspace/database/row IDs;
- return before/after summaries;
- avoid bulk/destructive actions until there is a proven safety model.

## Scope limits

No broad destructive, admin, or invite tools are included. Specifically:

- Row delete is available only via the experimental Yjs path (`appflowy_delete_database_row`),
  gated by two explicit env flags and Node.js.
- No view/page delete or bulk operations.
- No workspace admin or member management.
