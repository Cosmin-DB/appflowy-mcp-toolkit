# AppFlowy MCP Toolkit — coordination notes

Local-first pre-1.0 release candidate. Do not publish until Cosmin approves the
final external release review.

Working principle:
- Main assistant coordinates and reviews only.
- Implementation/research is delegated to focused subagents.
- Keep scope realistic; avoid overengineering.
- Public repo should remain generic: no private user-specific config, IDs, secrets, or workflows.
- Private/local usage can live outside the repo via env files or separate wrappers.
-- Future delegated tasks must be small, short, and independently verifiable. Avoid
  assigning one worker broad research + implementation + docs + release cleanup.

Current target:
A clean, self-host-friendly AppFlowy MCP toolkit with reusable Python client, CLI
inspection, MCP tools, guarded writes, optional self-hosted Docker tests, and honest
browser evidence.

No secrets in repo. Docker is allowed only for optional disposable AppFlowy testing.
Keep browser-rendering findings separate from API/collab data-plane verification.
