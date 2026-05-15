# Agent working rules for this repo

This repo is intended for multi-agent work.

## Coordination

- The coordinator owns scope, review, and final integration.
- Worker agents receive narrow tasks and should touch only their assigned files.
- Every worker must report what changed, tests run, and remaining risks.

## Safety

- Never read or commit real secrets.
- Never commit `.env`, tokens, cookies, magic links, OTPs, personal emails, real workspace IDs, or local dumps.
- Public examples must use fake IDs such as `ws_demo_001`.

## Scope

- Keep the first release read-only.
- Do not add Docker, caches, background sync, broad admin tools, or delete tools unless explicitly accepted.
- Prefer small tested modules over framework-heavy abstractions.

## Review checklist

- Tests pass.
- No secrets/private data.
- CLI/MCP behavior is generic.
- Errors are useful and redacted.
- No copied code from unlicensed/AGPL/license-conflicted repos.
