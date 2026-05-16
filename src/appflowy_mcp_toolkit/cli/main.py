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
    sub.add_parser(
        "setup-check",
        description=(
            "Check local runtime setup for optional collab/Yjs commands. "
            "Does not require AppFlowy credentials or network access."
        ),
    )
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

    create_verified_row = sub.add_parser("create-verified-row")
    create_verified_row.add_argument("--workspace-id", required=True)
    create_verified_row.add_argument("--database-id", required=True)
    create_verified_row.add_argument("--cells-json", default="{}")
    create_verified_row.add_argument("--document")
    create_verified_row.add_argument(
        "--skip-blob-diff",
        action="store_true",
        help="Skip blob/diff verification; useful while AppFlowy Web reports pending live rows",
    )
    create_verified_row.add_argument(
        "--execute", action="store_true", help="Actually create it; default is dry-run"
    )

    verify_row = sub.add_parser("verify-row")
    verify_row.add_argument("--workspace-id", required=True)
    verify_row.add_argument("--database-id", required=True)
    verify_row.add_argument("--row-id", required=True)
    verify_row.add_argument(
        "--skip-blob-diff",
        action="store_true",
        help="Skip blob/diff verification; useful while AppFlowy Web reports pending live rows",
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

    collab = sub.add_parser("collab-json")
    collab.add_argument("--workspace-id", required=True)
    collab.add_argument("--object-id", required=True)
    collab.add_argument("--collab-type", default="Database")

    row_orders = sub.add_parser("row-orders")
    row_orders.add_argument("--workspace-id", required=True)
    row_orders.add_argument("--database-id", required=True)

    blob_diff = sub.add_parser(
        "blob-diff",
        description=(
            "Read-only diagnostic for AppFlowy Web's database blob/diff endpoint. "
            "Returns row ids, operation types and doc-state byte counts without "
            "printing raw binary document state."
        ),
    )
    blob_diff.add_argument("--workspace-id", required=True)
    blob_diff.add_argument("--database-id", required=True)
    blob_diff.add_argument("--version", type=int, default=1)

    list_tasks = sub.add_parser("tasks")
    list_tasks.add_argument("--workspace-id", required=True)
    list_tasks.add_argument("--database-id", required=True)
    list_tasks.add_argument("--with-doc", action="store_true")

    create_task = sub.add_parser("create-task")
    create_task.add_argument("--workspace-id", required=True)
    create_task.add_argument("--database-id", required=True)
    create_task.add_argument("--task-key", required=True)
    create_task.add_argument("--description", required=True)
    create_task.add_argument("--status", default="To Do")
    create_task.add_argument("--document")
    create_task.add_argument("--skip-blob-diff", action="store_true")
    create_task.add_argument("--execute", action="store_true")

    update_task = sub.add_parser("update-task")
    update_task.add_argument("--workspace-id", required=True)
    update_task.add_argument("--database-id", required=True)
    update_task.add_argument("--task-key", required=True)
    update_task.add_argument("--description")
    update_task.add_argument("--status")
    update_task.add_argument("--document")
    update_task.add_argument("--skip-blob-diff", action="store_true")
    update_task.add_argument("--execute", action="store_true")

    move_task = sub.add_parser("move-task")
    move_task.add_argument("--workspace-id", required=True)
    move_task.add_argument("--database-id", required=True)
    move_task.add_argument("--task-key", required=True)
    move_task.add_argument("--status", required=True)
    move_task.add_argument("--execute", action="store_true")

    delete_task = sub.add_parser("delete-task")
    delete_task.add_argument("--workspace-id", required=True)
    delete_task.add_argument("--database-id", required=True)
    delete_task.add_argument("--row-id", required=True)
    delete_task.add_argument("--execute", action="store_true")

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

    managed_verified = sub.add_parser("managed-task-verified")
    managed_verified.add_argument("--workspace-id", required=True)
    managed_verified.add_argument("--database-id", required=True)
    managed_verified.add_argument("--task-key", required=True)
    managed_verified.add_argument("--description")
    managed_verified.add_argument("--status")
    managed_verified.add_argument("--document")
    managed_verified.add_argument(
        "--skip-blob-diff",
        action="store_true",
        help="Skip blob/diff verification; useful while AppFlowy Web reports pending live rows",
    )
    managed_verified.add_argument(
        "--execute", action="store_true", help="Actually upsert it; default is dry-run"
    )

    move = sub.add_parser("move-managed-task")
    move.add_argument("--workspace-id", required=True)
    move.add_argument("--database-id", required=True)
    move.add_argument("--task-key", required=True)
    move.add_argument("--status", required=True)
    move.add_argument("--execute", action="store_true", help="Actually move it; default is dry-run")

    delete_row = sub.add_parser(
        "delete-row",
        description=(
            "[EXPERIMENTAL] Delete a database row via Yjs collab mutation. "
            "Requires Node.js 18+ and yjs npm package. "
            "Dry-run by default; use --execute for a live write (requires "
            "APPFLOWY_ALLOW_WRITES=true and APPFLOWY_ALLOW_COLLAB_WRITES=true)."
        ),
    )
    delete_row.add_argument("--workspace-id", required=True)
    delete_row.add_argument("--database-id", required=True)
    delete_row.add_argument("--row-id", required=True)
    delete_row.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete the row (live write); default is dry-run",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "setup-check":
        from appflowy_mcp_toolkit.collab.collab_delete import check_collab_helper_setup

        print(to_json(check_collab_helper_setup()))
        return 0

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
        elif args.command == "create-verified-row":
            result = client.create_database_row_verified(
                args.workspace_id,
                args.database_id,
                cells=json.loads(args.cells_json),
                document=args.document,
                dry_run=not args.execute,
                include_blob_diff=not args.skip_blob_diff,
            )
        elif args.command == "verify-row":
            result = client.verify_database_row(
                args.workspace_id,
                args.database_id,
                args.row_id,
                include_blob_diff=not args.skip_blob_diff,
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
        elif args.command == "collab-json":
            result = client.get_collab_json(
                args.workspace_id,
                args.object_id,
                collab_type=args.collab_type,
            )
        elif args.command == "row-orders":
            result = client.get_database_row_orders(args.workspace_id, args.database_id)
        elif args.command == "blob-diff":
            result = client.get_database_blob_diff_summary(
                args.workspace_id,
                args.database_id,
                version=args.version,
            )
        elif args.command == "tasks":
            result = client.list_tasks(
                args.workspace_id,
                args.database_id,
                with_doc=args.with_doc,
            )
        elif args.command == "create-task":
            result = client.create_task(
                args.workspace_id,
                args.database_id,
                task_key=args.task_key,
                description=args.description,
                status=args.status,
                document=args.document,
                dry_run=not args.execute,
                include_blob_diff=not args.skip_blob_diff,
            )
        elif args.command == "update-task":
            result = client.update_task(
                args.workspace_id,
                args.database_id,
                task_key=args.task_key,
                description=args.description,
                status=args.status,
                document=args.document,
                dry_run=not args.execute,
                include_blob_diff=not args.skip_blob_diff,
            )
        elif args.command == "move-task":
            result = client.move_task(
                args.workspace_id,
                args.database_id,
                task_key=args.task_key,
                status=args.status,
                dry_run=not args.execute,
            )
        elif args.command == "delete-task":
            result = client.delete_task(
                args.workspace_id,
                args.database_id,
                args.row_id,
                dry_run=not args.execute,
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
        elif args.command == "managed-task-verified":
            result = client.upsert_managed_task_verified(
                args.workspace_id,
                args.database_id,
                task_key=args.task_key,
                description=args.description,
                status=args.status,
                document=args.document,
                dry_run=not args.execute,
                include_blob_diff=not args.skip_blob_diff,
            )
        elif args.command == "move-managed-task":
            result = client.move_managed_task_status(
                args.workspace_id,
                args.database_id,
                task_key=args.task_key,
                status=args.status,
                dry_run=not args.execute,
            )
        elif args.command == "delete-row":
            result = client.delete_database_row_collab(
                args.workspace_id,
                args.database_id,
                args.row_id,
                dry_run=not args.execute,
            )
        else:  # pragma: no cover
            raise AssertionError(args.command)
    print(to_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
