# Safety

This project is read-only first.

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

Write tools are out of scope for the initial release. Future write tools must:

- be disabled by default;
- require explicit opt-in;
- support dry-run previews where practical;
- validate target workspace/database/row IDs;
- return before/after summaries;
- avoid bulk/destructive actions until there is a proven safety model.
