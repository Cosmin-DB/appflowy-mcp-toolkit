from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from typing import Any

from appflowy_mcp_toolkit.client import AppFlowyClient
from appflowy_mcp_toolkit.formatting import to_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="appflowy-toolkit")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("health")
    sub.add_parser("workspaces")

    folder = sub.add_parser("folder")
    folder.add_argument("--workspace-id", required=True)
    folder.add_argument("--depth", type=int)
    folder.add_argument("--root-view-id")

    databases = sub.add_parser("databases")
    databases.add_argument("--workspace-id", required=True)

    fields = sub.add_parser("fields")
    fields.add_argument("--workspace-id", required=True)
    fields.add_argument("--database-id", required=True)

    rows = sub.add_parser("rows")
    rows.add_argument("--workspace-id", required=True)
    rows.add_argument("--database-id", required=True)

    details = sub.add_parser("row-details")
    details.add_argument("--workspace-id", required=True)
    details.add_argument("--database-id", required=True)
    details.add_argument("--ids", required=True, help="Comma-separated row ids")
    details.add_argument("--with-doc", action="store_true")

    create_workspace = sub.add_parser("create-workspace")
    create_workspace.add_argument("--name", required=True)
    create_workspace.add_argument(
        "--execute", action="store_true", help="Actually create it; default is dry-run"
    )

    create_row = sub.add_parser("create-row")
    create_row.add_argument("--workspace-id", required=True)
    create_row.add_argument("--database-id", required=True)
    create_row.add_argument("--cells-json", default="{}")
    create_row.add_argument("--document")
    create_row.add_argument(
        "--execute", action="store_true", help="Actually create it; default is dry-run"
    )

    upsert_row = sub.add_parser("upsert-row")
    upsert_row.add_argument("--workspace-id", required=True)
    upsert_row.add_argument("--database-id", required=True)
    upsert_row.add_argument("--pre-hash")
    upsert_row.add_argument("--cells-json", default="{}")
    upsert_row.add_argument("--document")
    upsert_row.add_argument(
        "--execute", action="store_true", help="Actually upsert it; default is dry-run"
    )

    options = sub.add_parser("select-options")
    options.add_argument("--workspace-id", required=True)
    options.add_argument("--database-id", required=True)
    options.add_argument("--field-name", default="Status")

    managed = sub.add_parser("managed-task")
    managed.add_argument("--workspace-id", required=True)
    managed.add_argument("--database-id", required=True)
    managed.add_argument("--task-key", required=True)
    managed.add_argument("--description")
    managed.add_argument("--status")
    managed.add_argument("--document")
    managed.add_argument(
        "--execute", action="store_true", help="Actually upsert it; default is dry-run"
    )

    move = sub.add_parser("move-managed-task")
    move.add_argument("--workspace-id", required=True)
    move.add_argument("--database-id", required=True)
    move.add_argument("--task-key", required=True)
    move.add_argument("--status", required=True)
    move.add_argument("--execute", action="store_true", help="Actually move it; default is dry-run")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    with AppFlowyClient() as client:
        if args.command == "health":
            result: Any = client.health_check()
        elif args.command == "workspaces":
            result = client.list_workspaces(include_member_count=True, include_role=True)
        elif args.command == "folder":
            result = client.get_folder(
                args.workspace_id, depth=args.depth, root_view_id=args.root_view_id
            )
        elif args.command == "databases":
            result = client.list_databases(args.workspace_id)
        elif args.command == "fields":
            result = client.list_database_fields(args.workspace_id, args.database_id)
        elif args.command == "rows":
            result = client.list_database_row_ids(args.workspace_id, args.database_id)
        elif args.command == "row-details":
            ids = [part.strip() for part in args.ids.split(",") if part.strip()]
            result = client.get_database_rows(
                args.workspace_id, args.database_id, ids, with_doc=args.with_doc
            )
        elif args.command == "create-workspace":
            result = client.create_workspace(args.name, dry_run=not args.execute)
        elif args.command == "create-row":
            result = client.create_database_row(
                args.workspace_id,
                args.database_id,
                cells=json.loads(args.cells_json),
                document=args.document,
                dry_run=not args.execute,
            )
        elif args.command == "upsert-row":
            result = client.upsert_database_row(
                args.workspace_id,
                args.database_id,
                pre_hash=args.pre_hash,
                cells=json.loads(args.cells_json),
                document=args.document,
                dry_run=not args.execute,
            )
        elif args.command == "select-options":
            result = client.list_select_options(
                args.workspace_id, args.database_id, field_name=args.field_name
            )
        elif args.command == "managed-task":
            result = client.upsert_managed_task(
                args.workspace_id,
                args.database_id,
                task_key=args.task_key,
                description=args.description,
                status=args.status,
                document=args.document,
                dry_run=not args.execute,
            )
        elif args.command == "move-managed-task":
            result = client.move_managed_task_status(
                args.workspace_id,
                args.database_id,
                task_key=args.task_key,
                status=args.status,
                dry_run=not args.execute,
            )
        else:  # pragma: no cover
            raise AssertionError(args.command)
    print(to_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
