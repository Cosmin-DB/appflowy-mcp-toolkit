# Development

Install locally:

```bash
python -m pip install -e '.[dev,mcp]'
```

Quality gates:

```bash
python -m pytest
python -m ruff format --check .
python -m ruff check .
python -m mypy src tests
```

Live AppFlowy tests are intentionally not part of the default suite. If added later, they must be opt-in, read-only by default, and must never run in public CI without explicit disposable credentials.
