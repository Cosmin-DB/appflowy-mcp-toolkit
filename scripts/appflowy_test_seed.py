from __future__ import annotations

import json
import os
import shlex
import sys
from pathlib import Path
from typing import Any

import httpx

from appflowy_mcp_toolkit.client import AppFlowyClient
from appflowy_mcp_toolkit.config import AppFlowyConfig

ROOT = Path(__file__).resolve().parents[1]
GENERATED_ENV = ROOT / ".env.selfhosted.generated"


def main() -> int:
    base_url = os.getenv("APPFLOWY_SELFHOSTED_BASE_URL", "http://localhost").rstrip("/")
    if "appflowy.cloud" in base_url and os.getenv("APPFLOWY_SELFHOSTED_ALLOW_OFFICIAL") != "true":
        print(
            "Refusing to seed official AppFlowy cloud from the self-hosted script.", file=sys.stderr
        )
        return 2

    existing = load_generated_env()
    if (
        existing
        and existing.get("APPFLOWY_BASE_URL", "").rstrip("/") == base_url
        and validate_generated_env(existing)
    ):
        print(f"Reusing valid {GENERATED_ENV}")
        print(f"workspace_id={existing['APPFLOWY_LIVE_WORKSPACE_ID']}")
        print(f"database_id={existing['APPFLOWY_LIVE_DATABASE_ID']}")
        return 0

    email = os.getenv("APPFLOWY_TEST_EMAIL", "mcp-test@example.test")
    password = os.getenv("APPFLOWY_TEST_PASSWORD", "appflowy-mcp-test-password")

    tokens = signup_or_login(base_url, email, password)
    verify_cloud_user(base_url, tokens["access_token"])
    config = AppFlowyConfig(
        base_url=base_url,
        access_token=tokens["access_token"],
        refresh_token=tokens.get("refresh_token"),
        allow_writes=True,
    )

    with AppFlowyClient(config) as client:
        workspace_id = ensure_workspace(client)
        database_id = find_task_database(client, workspace_id)

    if database_id is None:
        print(
            "No database with Description and Status fields was found. "
            "Open AppFlowy Web once or seed a To-dos board, then rerun this script.",
            file=sys.stderr,
        )
        return 3

    write_generated_env(base_url, tokens, workspace_id, database_id, email, password)
    print(f"Wrote {GENERATED_ENV}")
    print(f"workspace_id={workspace_id}")
    print(f"database_id={database_id}")
    return 0


def load_generated_env() -> dict[str, str]:
    if not GENERATED_ENV.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in GENERATED_ENV.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        try:
            value = shlex.split(raw_value)[0]
        except (IndexError, ValueError):
            value = raw_value.strip().strip("'\"")
        values[key] = value
    return values


def validate_generated_env(values: dict[str, str]) -> bool:
    required = (
        "APPFLOWY_BASE_URL",
        "APPFLOWY_ACCESS_TOKEN",
        "APPFLOWY_LIVE_WORKSPACE_ID",
        "APPFLOWY_LIVE_DATABASE_ID",
    )
    if any(not values.get(key) for key in required):
        return False
    config = AppFlowyConfig(
        base_url=values["APPFLOWY_BASE_URL"].rstrip("/"),
        access_token=values["APPFLOWY_ACCESS_TOKEN"],
        refresh_token=values.get("APPFLOWY_REFRESH_TOKEN") or None,
        allow_writes=True,
    )
    try:
        with AppFlowyClient(config) as client:
            client.list_database_fields(
                values["APPFLOWY_LIVE_WORKSPACE_ID"],
                values["APPFLOWY_LIVE_DATABASE_ID"],
            )
    except Exception:
        return False
    return True


def signup_or_login(base_url: str, email: str, password: str) -> dict[str, str]:
    with httpx.Client(timeout=30.0) as client:
        signup_payload = {"email": email, "password": password}
        signup = client.post(f"{base_url}/gotrue/signup", json=signup_payload)
        if signup.status_code not in {200, 201, 400, 422}:
            signup.raise_for_status()

        token = client.post(
            f"{base_url}/gotrue/token",
            params={"grant_type": "password"},
            json={"email": email, "password": password},
        )
        token.raise_for_status()
        data = token.json()
        access_token = data.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise RuntimeError(f"GoTrue token response did not include access_token: {data!r}")
        refresh_token = data.get("refresh_token")
        return {
            "access_token": access_token,
            **({"refresh_token": refresh_token} if isinstance(refresh_token, str) else {}),
        }


def verify_cloud_user(base_url: str, access_token: str) -> None:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(f"{base_url}/api/user/verify/{access_token}")
        response.raise_for_status()


def ensure_workspace(client: AppFlowyClient) -> str:
    workspaces = client.list_workspaces()
    workspace_id = first_id(workspaces, "workspace_id") or first_id(workspaces, "id")
    if workspace_id:
        return workspace_id

    created = client.create_workspace("MCP Self-Hosted Tests", dry_run=False)
    workspace_id = extract_any_id(created, ("workspace_id", "id"))
    if workspace_id is None:
        workspaces = client.list_workspaces()
        workspace_id = first_id(workspaces, "workspace_id") or first_id(workspaces, "id")
    if not workspace_id:
        raise RuntimeError(f"Could not discover/create workspace; create response: {created!r}")
    return workspace_id


def find_task_database(client: AppFlowyClient, workspace_id: str) -> str | None:
    for database in client.list_databases(workspace_id):
        database_id = extract_any_id(database, ("database_id", "id", "databaseId"))
        if not database_id:
            continue
        fields = client.list_database_fields(workspace_id, database_id)
        names = {field.get("name") for field in fields if isinstance(field, dict)}
        if {"Description", "Status"}.issubset(names):
            return database_id
    return None


def first_id(items: list[dict[str, Any]], key: str) -> str | None:
    for item in items:
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def extract_any_id(payload: Any, keys: tuple[str, ...]) -> str | None:
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
        data = payload.get("data")
        if isinstance(data, dict):
            return extract_any_id(data, keys)
    return None


def write_generated_env(
    base_url: str,
    tokens: dict[str, str],
    workspace_id: str,
    database_id: str,
    email: str,
    password: str,
) -> None:
    values = {
        "APPFLOWY_BASE_URL": base_url,
        "APPFLOWY_ACCESS_TOKEN": tokens["access_token"],
        "APPFLOWY_REFRESH_TOKEN": tokens.get("refresh_token", ""),
        "APPFLOWY_ALLOW_WRITES": "true",
        "APPFLOWY_ALLOW_COLLAB_WRITES": "true",
        "APPFLOWY_LIVE_WORKSPACE_ID": workspace_id,
        "APPFLOWY_LIVE_DATABASE_ID": database_id,
        "APPFLOWY_SELFHOSTED_TESTS": "true",
        "APPFLOWY_LIVE_TESTS": "true",
        "APPFLOWY_BROWSER_EMAIL": email,
        "APPFLOWY_BROWSER_PASSWORD": password,
    }
    GENERATED_ENV.write_text(
        "\n".join(f"{key}={shell_quote(value)}" for key, value in values.items()) + "\n",
        encoding="utf-8",
    )
    metadata_path = ROOT / ".env.selfhosted.generated.json"
    metadata_path.write_text(
        json.dumps(
            {k: v for k, v in values.items() if "TOKEN" not in k and "PASSWORD" not in k},
            indent=2,
        ),
        encoding="utf-8",
    )


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


if __name__ == "__main__":
    raise SystemExit(main())
