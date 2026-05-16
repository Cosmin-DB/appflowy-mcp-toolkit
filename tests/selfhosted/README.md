# Self-Hosted Tests

These tests run the same destructive task lifecycle against a local AppFlowy stack.

Run:

```bash
scripts/appflowy_test_env_up.sh
python scripts/appflowy_test_seed.py
set -a
source .env.selfhosted.generated
set +a
APPFLOWY_SELFHOSTED_TESTS=true uv run pytest tests/selfhosted -q
```

They refuse to run by default and should never target AppFlowy official cloud.
