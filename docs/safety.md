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

## Scope limits

No broad destructive, admin, or invite tools are included. Specifically:

- No row delete (no confirmed public REST endpoint exists).
- No view/page delete or bulk operations.
- No workspace admin or member management.

Future write tools must:

- be disabled by default;
- require explicit opt-in via `APPFLOWY_ALLOW_WRITES`;
- support dry-run previews where practical;
- validate target workspace/database/row IDs;
- return before/after summaries;
- avoid bulk/destructive actions until there is a proven safety model.
