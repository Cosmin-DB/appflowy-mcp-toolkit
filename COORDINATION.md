# AppFlowy MCP Toolkit — coordination notes

Local-first repo draft. Do not publish until a clean initial version exists.

Working principle:
- Main assistant coordinates and reviews only.
- Implementation/research is delegated to focused subagents.
- Keep scope realistic; avoid overengineering.
- Public repo should remain generic: no private user-specific config, IDs, secrets, or workflows.
- Private/local usage can live outside the repo via env files or separate wrappers.
- After M6.5, feature work pauses until the experimental delete baseline is cleaned,
  reviewed, and committed.
- Future delegated tasks must be small, short, and independently verifiable. Avoid
  assigning one worker broad research + implementation + docs + release cleanup.

Initial target:
A clean, self-host-friendly AppFlowy MCP toolkit with reusable Python client, CLI inspection, MCP read-only tools first, then safe write operations.

No secrets in repo. No Docker unless/ until it is clearly useful.
