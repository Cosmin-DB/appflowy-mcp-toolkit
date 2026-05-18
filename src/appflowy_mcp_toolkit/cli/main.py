from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from appflowy_mcp_toolkit.client import AppFlowyClient
from appflowy_mcp_toolkit.formatting import to_json
from appflowy_mcp_toolkit.workflows import safe_workflows


def _run_doctor(*, network: bool) -> dict[str, Any]:  # noqa: C901
    """Build the doctor report.  Safe offline by default."""
    import importlib.metadata
    import importlib.util

    # ---------- package version ----------
    try:
        pkg_version = importlib.metadata.version("appflowy-mcp-toolkit")
    except importlib.metadata.PackageNotFoundError:
        pkg_version = "unknown (editable install?)"

    # ---------- environment / credentials ----------
    base_url_raw = os.environ.get("APPFLOWY_BASE_URL", "")
    token_raw = os.environ.get("APPFLOWY_ACCESS_TOKEN", "")
    env: dict[str, Any] = {
        "APPFLOWY_BASE_URL": base_url_raw or "(default: https://beta.appflowy.cloud)",
        "APPFLOWY_ACCESS_TOKEN_present": bool(token_raw),
        "APPFLOWY_ALLOW_WRITES": os.environ.get("APPFLOWY_ALLOW_WRITES", "") or "(not set)",
        "APPFLOWY_ALLOW_COLLAB_WRITES": (
            os.environ.get("APPFLOWY_ALLOW_COLLAB_WRITES", "") or "(not set)"
        ),
    }

    # ---------- runtime basics ----------
    runtime: dict[str, Any] = {
        "python_version": sys.version,
        "python_executable": sys.executable,
    }

    # ---------- collab helper (local, no network) ----------
    from appflowy_mcp_toolkit.collab.collab_delete import check_collab_helper_setup

    collab_setup = check_collab_helper_setup()

    # ---------- MCP server import ----------
    mcp_available = importlib.util.find_spec("mcp") is not None
    mcp_import_error: str | None
    try:
        import appflowy_mcp_toolkit.mcp.server  # noqa: F401

        mcp_server_importable = True
    except Exception as exc:  # pragma: no cover
        mcp_server_importable = False
        mcp_import_error = str(exc)
    else:
        mcp_import_error = None

    mcp_info: dict[str, Any] = {
        "mcp_package_available": mcp_available,
        "mcp_server_importable": mcp_server_importable,
    }
    if mcp_import_error is not None:
        mcp_info["mcp_import_error"] = mcp_import_error

    # ---------- optional network check ----------
    network_result: dict[str, Any] | None = None
    if network:
        if not token_raw:
            network_result = {
                "ok": False,
                "error": "APPFLOWY_ACCESS_TOKEN is not set; cannot perform network check",
            }
        else:
            try:
                with AppFlowyClient() as client:
                    network_result = client.health_check()
            except Exception as exc:
                network_result = {"ok": False, "error": str(exc)}

    # ---------- recommended actions ----------
    actions: list[str] = []
    if not token_raw:
        actions.append(
            "Set APPFLOWY_ACCESS_TOKEN to your AppFlowy personal token to enable API commands."
        )
    if not base_url_raw:
        actions.append(
            "Set APPFLOWY_BASE_URL if you are using a self-hosted instance "
            "(default is https://beta.appflowy.cloud)."
        )
    if not collab_setup.get("ok"):
        actions.append(
            "Run: " + collab_setup.get("install_command", "npm install in the collab helper dir")
        )
    if not mcp_available:
        actions.append(
            "Install or reinstall the package so the MCP server dependency is available: "
            "pipx install --force appflowy-mcp-toolkit"
        )
    if not actions:
        actions.append("All checks passed. Run `appflowy-toolkit workspaces` to get started.")

    report: dict[str, Any] = {
        "version": pkg_version,
        "runtime": runtime,
        "env": env,
        "collab_helper": collab_setup,
        "mcp": mcp_info,
        "next_steps": actions,
    }
    if network:
        report["network_check"] = network_result
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="appflowy-toolkit")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser(
        "doctor",
        description=(
            "Check local installation, environment, and optional network connectivity. "
            "Safe to run offline; does not require AppFlowy credentials by default."
        ),
    )
    doctor.add_argument(
        "--network",
        "--check-appflowy",
        action="store_true",
        default=False,
        dest="network",
        help="Also call health_check via AppFlowyClient (requires APPFLOWY_ACCESS_TOKEN).",
    )

    sub.add_parser("health")

    template_categories = sub.add_parser(
        "template-categories",
        description="List AppFlowy template categories (read-only, no credentials required).",
    )
    template_categories.add_argument("--name-contains")
    template_categories.add_argument("--category-type", type=int)

    template_category = sub.add_parser(
        "template-category",
        description="Get a single AppFlowy template category by id.",
    )
    template_category.add_argument("--category-id", required=True)

    template_creators = sub.add_parser(
        "template-creators",
        description="List AppFlowy template creators (read-only, no credentials required).",
    )
    template_creators.add_argument("--name-contains")

    template_creator = sub.add_parser(
        "template-creator",
        description="Get a single AppFlowy template creator by id.",
    )
    template_creator.add_argument("--creator-id", required=True)

    templates = sub.add_parser(
        "templates",
        description="List AppFlowy templates (read-only, no credentials required).",
    )
    templates.add_argument("--category-id")
    templates.add_argument("--is-featured", action=argparse.BooleanOptionalAction, default=None)
    templates.add_argument("--is-new-template", action=argparse.BooleanOptionalAction, default=None)
    templates.add_argument("--name-contains")

    template = sub.add_parser(
        "template",
        description="Get a single AppFlowy template by view_id.",
    )
    template.add_argument("--view-id", required=True)

    template_homepage = sub.add_parser(
        "template-homepage",
        description="Get the AppFlowy template home page (featured/new templates and categories).",
    )
    template_homepage.add_argument("--per-count", type=int)
    sub.add_parser(
        "workflows",
        description=(
            "Print safe AppFlowy operating paths for agents. "
            "This is offline guidance and does not require credentials."
        ),
    )
    sub.add_parser(
        "setup-check",
        description=(
            "Check local collab/Yjs helper setup only. "
            "Alias for the collab section of `doctor`. "
            "Does not require AppFlowy credentials or network access."
        ),
    )
    sub.add_parser("workspaces")
    sub.add_parser("server-info")
    sub.add_parser("user-profile")
    sub.add_parser("user-workspace-info")

    workspace_settings = sub.add_parser("workspace-settings")
    workspace_settings.add_argument("--workspace-id", required=True)

    workspace_members = sub.add_parser("workspace-members")
    workspace_members.add_argument("--workspace-id", required=True)

    workspace_usage = sub.add_parser("workspace-usage")
    workspace_usage.add_argument("--workspace-id", required=True)

    publish_namespace = sub.add_parser("publish-namespace")
    publish_namespace.add_argument("--workspace-id", required=True)

    publish_default = sub.add_parser("publish-default")
    publish_default.add_argument("--workspace-id", required=True)

    published_pages = sub.add_parser("published-pages")
    published_pages.add_argument("--workspace-id", required=True)

    published_page_info = sub.add_parser("published-page-info")
    published_page_info.add_argument("--view-id", required=True)
    published_page_info.add_argument("--include-unpublished", action="store_true", default=False)

    publish_page = sub.add_parser(
        "publish-page",
        description=(
            "Publish an AppFlowy page view. "
            "Requires APPFLOWY_ALLOW_WRITES=true and APPFLOWY_ALLOW_PUBLISH_WRITES=true "
            "when --execute is passed."
        ),
    )
    publish_page.add_argument("--workspace-id", required=True)
    publish_page.add_argument("--view-id", required=True)
    publish_page.add_argument("--publish-name")
    publish_page.add_argument(
        "--visible-database-view-ids",
        help="Comma-separated list of database view ids to make visible in the published page.",
    )
    publish_page.add_argument(
        "--comments-enabled", action=argparse.BooleanOptionalAction, default=None
    )
    publish_page.add_argument(
        "--duplicate-enabled", action=argparse.BooleanOptionalAction, default=None
    )
    publish_page.add_argument("--execute", action="store_true")

    unpublish_page = sub.add_parser(
        "unpublish-page",
        description=(
            "Unpublish an AppFlowy page view. "
            "Requires APPFLOWY_ALLOW_WRITES=true and APPFLOWY_ALLOW_PUBLISH_WRITES=true "
            "when --execute is passed."
        ),
    )
    unpublish_page.add_argument("--workspace-id", required=True)
    unpublish_page.add_argument("--view-id", required=True)
    unpublish_page.add_argument("--execute", action="store_true")

    dup_pub = sub.add_parser(
        "duplicate-published-page",
        description=(
            "Duplicate a published AppFlowy page/template into a destination view. "
            "Requires APPFLOWY_ALLOW_WRITES=true when --execute is passed."
        ),
    )
    dup_pub.add_argument("--workspace-id", required=True)
    dup_pub.add_argument("--published-view-id", required=True)
    dup_pub.add_argument("--dest-view-id", required=True)
    dup_pub.add_argument("--execute", action="store_true")

    inst_tmpl = sub.add_parser(
        "instantiate-template",
        description=(
            "Instantiate a published AppFlowy template into a destination view. "
            "Only works for pages/templates already published on AppFlowy. "
            "Requires APPFLOWY_ALLOW_WRITES=true when --execute is passed."
        ),
    )
    inst_tmpl.add_argument("--workspace-id", required=True)
    inst_tmpl.add_argument("--template-view-id", required=True)
    inst_tmpl.add_argument("--dest-view-id", required=True)
    inst_tmpl.add_argument("--execute", action="store_true")

    create_space = sub.add_parser("create-space")
    create_space.add_argument("--workspace-id", required=True)
    create_space.add_argument("--name", required=True)
    create_space.add_argument("--space-permission", type=int, default=0)
    create_space.add_argument("--space-icon", default="")
    create_space.add_argument("--space-icon-color", default="")
    create_space.add_argument("--view-id")
    create_space.add_argument("--execute", action="store_true")

    update_space = sub.add_parser("update-space")
    update_space.add_argument("--workspace-id", required=True)
    update_space.add_argument("--view-id", required=True)
    update_space.add_argument("--name", required=True)
    update_space.add_argument("--space-permission", type=int, default=0)
    update_space.add_argument("--space-icon", default="")
    update_space.add_argument("--space-icon-color", default="")
    update_space.add_argument("--execute", action="store_true")

    file_storage_usage = sub.add_parser("file-storage-usage")
    file_storage_usage.add_argument("--workspace-id", required=True)

    file_storage_blobs = sub.add_parser("file-storage-blobs")
    file_storage_blobs.add_argument("--workspace-id", required=True)

    file_metadata = sub.add_parser("file-metadata")
    file_metadata.add_argument("--workspace-id", required=True)
    file_metadata.add_argument("--file-id", required=True)

    file_metadata_v1 = sub.add_parser("file-metadata-v1")
    file_metadata_v1.add_argument("--workspace-id", required=True)
    file_metadata_v1.add_argument("--parent-dir", required=True)
    file_metadata_v1.add_argument("--file-id", required=True)

    upload_file_v1 = sub.add_parser("upload-file-v1")
    upload_file_v1.add_argument("--workspace-id", required=True)
    upload_file_v1.add_argument("--parent-dir", required=True)
    upload_file_v1.add_argument("--file-path", required=True)
    upload_file_v1.add_argument("--content-type")
    upload_file_v1.add_argument("--execute", action="store_true")

    download_file_v1 = sub.add_parser("download-file-v1")
    download_file_v1.add_argument("--workspace-id", required=True)
    download_file_v1.add_argument("--parent-dir", required=True)
    download_file_v1.add_argument("--file-id", required=True)
    download_file_v1.add_argument("--output", required=True)

    delete_file_v1 = sub.add_parser("delete-file-v1")
    delete_file_v1.add_argument("--workspace-id", required=True)
    delete_file_v1.add_argument("--parent-dir", required=True)
    delete_file_v1.add_argument("--file-id", required=True)
    delete_file_v1.add_argument("--execute", action="store_true")

    upload_media = sub.add_parser("upload-media-file")
    upload_media.add_argument("--workspace-id", required=True)
    upload_media.add_argument("--database-id", required=True)
    upload_media.add_argument("--file-path", required=True)
    upload_media.add_argument("--name")
    upload_media.add_argument("--content-type")
    upload_media.add_argument("--file-type")
    upload_media.add_argument("--execute", action="store_true")

    folder = sub.add_parser("folder")
    folder.add_argument("--workspace-id", required=True)
    folder.add_argument("--depth", type=int)
    folder.add_argument("--root-view-id")

    create_folder = sub.add_parser("create-folder")
    create_folder.add_argument("--workspace-id", required=True)
    create_folder.add_argument("--parent-view-id", required=True)
    create_folder.add_argument("--layout", type=int, default=0)
    create_folder.add_argument("--name")
    create_folder.add_argument("--view-id")
    create_folder.add_argument("--database-id")
    create_folder.add_argument("--execute", action="store_true")

    page = sub.add_parser("page-view")
    page.add_argument("--workspace-id", required=True)
    page.add_argument("--view-id", required=True)

    create_page = sub.add_parser("create-page")
    create_page.add_argument("--workspace-id", required=True)
    create_page.add_argument("--parent-view-id", required=True)
    create_page.add_argument("--layout", type=int, default=0, help="AppFlowy ViewLayout integer")
    create_page.add_argument("--name")
    create_page.add_argument("--page-data-json")
    create_page.add_argument("--view-id")
    create_page.add_argument("--collab-id")
    create_page.add_argument("--execute", action="store_true")

    update_page = sub.add_parser("update-page")
    update_page.add_argument("--workspace-id", required=True)
    update_page.add_argument("--view-id", required=True)
    update_page.add_argument("--name", required=True)
    update_page.add_argument("--icon-json")
    update_page.add_argument("--is-locked", action=argparse.BooleanOptionalAction, default=None)
    update_page.add_argument("--extra-json")
    update_page.add_argument("--execute", action="store_true")

    rename_page = sub.add_parser("rename-page")
    rename_page.add_argument("--workspace-id", required=True)
    rename_page.add_argument("--view-id", required=True)
    rename_page.add_argument("--name", required=True)
    rename_page.add_argument("--execute", action="store_true")

    favorite_page = sub.add_parser("favorite-page")
    favorite_page.add_argument("--workspace-id", required=True)
    favorite_page.add_argument("--view-id", required=True)
    favorite_page.add_argument(
        "--is-favorite",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Use --no-is-favorite to remove the page from favorites.",
    )
    favorite_page.add_argument("--is-pinned", action=argparse.BooleanOptionalAction, default=False)
    favorite_page.add_argument("--execute", action="store_true")

    remove_page_icon = sub.add_parser("remove-page-icon")
    remove_page_icon.add_argument("--workspace-id", required=True)
    remove_page_icon.add_argument("--view-id", required=True)
    remove_page_icon.add_argument("--execute", action="store_true")

    append_page_blocks = sub.add_parser("append-page-blocks")
    append_page_blocks.add_argument("--workspace-id", required=True)
    append_page_blocks.add_argument("--view-id", required=True)
    append_page_blocks.add_argument("--blocks-json", required=True)
    append_page_blocks.add_argument("--execute", action="store_true")

    move_page = sub.add_parser("move-page")
    move_page.add_argument("--workspace-id", required=True)
    move_page.add_argument("--view-id", required=True)
    move_page.add_argument("--new-parent-view-id", required=True)
    move_page.add_argument("--prev-view-id")
    move_page.add_argument("--execute", action="store_true")

    reorder_favorite = sub.add_parser("reorder-favorite-page")
    reorder_favorite.add_argument("--workspace-id", required=True)
    reorder_favorite.add_argument("--view-id", required=True)
    reorder_favorite.add_argument("--prev-view-id")
    reorder_favorite.add_argument("--execute", action="store_true")

    duplicate_page = sub.add_parser("duplicate-page")
    duplicate_page.add_argument("--workspace-id", required=True)
    duplicate_page.add_argument("--view-id", required=True)
    duplicate_page.add_argument("--suffix")
    duplicate_page.add_argument("--execute", action="store_true")

    create_page_database = sub.add_parser("create-page-database")
    create_page_database.add_argument("--workspace-id", required=True)
    create_page_database.add_argument("--view-id", required=True)
    create_page_database.add_argument("--layout", type=int, required=True)
    create_page_database.add_argument("--name")
    create_page_database.add_argument("--execute", action="store_true")

    trash_page = sub.add_parser("trash-page")
    trash_page.add_argument("--workspace-id", required=True)
    trash_page.add_argument("--view-id", required=True)
    trash_page.add_argument("--execute", action="store_true")

    restore_page = sub.add_parser("restore-page")
    restore_page.add_argument("--workspace-id", required=True)
    restore_page.add_argument("--view-id", required=True)
    restore_page.add_argument("--execute", action="store_true")

    delete_trash_page = sub.add_parser("delete-trash-page")
    delete_trash_page.add_argument("--workspace-id", required=True)
    delete_trash_page.add_argument("--view-id", required=True)
    delete_trash_page.add_argument("--execute", action="store_true")

    add_recent_pages = sub.add_parser("add-recent-pages")
    add_recent_pages.add_argument("--workspace-id", required=True)
    add_recent_pages.add_argument("--view-ids", required=True, help="Comma-separated view ids")
    add_recent_pages.add_argument("--execute", action="store_true")

    restore_all_pages = sub.add_parser("restore-all-pages")
    restore_all_pages.add_argument("--workspace-id", required=True)
    restore_all_pages.add_argument("--execute", action="store_true")

    delete_all_trash_pages = sub.add_parser("delete-all-trash-pages")
    delete_all_trash_pages.add_argument("--workspace-id", required=True)
    delete_all_trash_pages.add_argument("--execute", action="store_true")

    recent = sub.add_parser("recent")
    recent.add_argument("--workspace-id", required=True)

    favorites = sub.add_parser("favorites")
    favorites.add_argument("--workspace-id", required=True)

    trash = sub.add_parser("trash")
    trash.add_argument("--workspace-id", required=True)

    databases = sub.add_parser("databases")
    databases.add_argument("--workspace-id", required=True)

    fields = sub.add_parser("fields")
    fields.add_argument("--workspace-id", required=True)
    fields.add_argument("--database-id", required=True)

    create_field = sub.add_parser("create-field")
    create_field.add_argument("--workspace-id", required=True)
    create_field.add_argument("--database-id", required=True)
    create_field.add_argument("--name", required=True)
    create_field.add_argument("--field-type", type=int, required=True)
    create_field.add_argument("--type-option-data-json")
    create_field.add_argument("--execute", action="store_true")

    add_select_option = sub.add_parser("add-select-option")
    add_select_option.add_argument("--workspace-id", required=True)
    add_select_option.add_argument("--database-id", required=True)
    add_select_option.add_argument("--name", required=True)
    add_select_option.add_argument("--field-name", default="Status")
    add_select_option.add_argument("--color", default="Purple")
    add_select_option.add_argument("--option-id")
    add_select_option.add_argument("--view-id")
    add_select_option.add_argument("--execute", action="store_true")

    rename_select_option = sub.add_parser("rename-select-option")
    rename_select_option.add_argument("--workspace-id", required=True)
    rename_select_option.add_argument("--database-id", required=True)
    rename_select_option.add_argument("--new-name", required=True)
    rename_select_option.add_argument("--field-name", default="Status")
    rename_select_option.add_argument("--option-id")
    rename_select_option.add_argument("--option-name")
    rename_select_option.add_argument("--execute", action="store_true")

    hide_select_option = sub.add_parser("hide-select-option")
    hide_select_option.add_argument("--workspace-id", required=True)
    hide_select_option.add_argument("--database-id", required=True)
    hide_select_option.add_argument("--field-name", default="Status")
    hide_select_option.add_argument("--option-id")
    hide_select_option.add_argument("--option-name")
    hide_select_option.add_argument("--view-id")
    hide_select_option.add_argument("--execute", action="store_true")

    show_select_option = sub.add_parser("show-select-option")
    show_select_option.add_argument("--workspace-id", required=True)
    show_select_option.add_argument("--database-id", required=True)
    show_select_option.add_argument("--field-name", default="Status")
    show_select_option.add_argument("--option-id")
    show_select_option.add_argument("--option-name")
    show_select_option.add_argument("--view-id")
    show_select_option.add_argument("--execute", action="store_true")

    rows = sub.add_parser("rows")
    rows.add_argument("--workspace-id", required=True)
    rows.add_argument("--database-id", required=True)

    updated_rows = sub.add_parser("updated-rows")
    updated_rows.add_argument("--workspace-id", required=True)
    updated_rows.add_argument("--database-id", required=True)
    updated_rows.add_argument(
        "--after",
        help="Optional RFC3339 timestamp. Defaults server-side to about one hour ago.",
    )

    quick_notes = sub.add_parser("quick-notes")
    quick_notes.add_argument("--workspace-id", required=True)
    quick_notes.add_argument("--search-term")
    quick_notes.add_argument("--offset", type=int)
    quick_notes.add_argument("--limit", type=int)

    create_quick_note = sub.add_parser("create-quick-note")
    create_quick_note.add_argument("--workspace-id", required=True)
    create_quick_note.add_argument(
        "--data-json",
        help="Quick-note JSON data. If omitted, AppFlowy receives data=null.",
    )
    create_quick_note.add_argument(
        "--execute", action="store_true", help="Actually create it; default is dry-run"
    )

    update_quick_note = sub.add_parser("update-quick-note")
    update_quick_note.add_argument("--workspace-id", required=True)
    update_quick_note.add_argument("--quick-note-id", required=True)
    update_quick_note.add_argument("--data-json", required=True)
    update_quick_note.add_argument(
        "--execute", action="store_true", help="Actually update it; default is dry-run"
    )

    delete_quick_note = sub.add_parser("delete-quick-note")
    delete_quick_note.add_argument("--workspace-id", required=True)
    delete_quick_note.add_argument("--quick-note-id", required=True)
    delete_quick_note.add_argument(
        "--execute", action="store_true", help="Actually delete it; default is dry-run"
    )

    search = sub.add_parser("search")
    search.add_argument("--workspace-id", required=True)
    search.add_argument("--query", required=True)
    search.add_argument("--limit", type=int)
    search.add_argument("--preview-size", type=int)
    search.add_argument(
        "--score",
        type=float,
        help="Optional minimum relevance score. Defaults server-side to 0.2.",
    )

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

    create_typed_row = sub.add_parser("create-typed-row")
    create_typed_row.add_argument("--workspace-id", required=True)
    create_typed_row.add_argument("--database-id", required=True)
    create_typed_row.add_argument(
        "--values-json",
        required=True,
        help="Human-friendly field values keyed by AppFlowy field name or id",
    )
    create_typed_row.add_argument("--document")
    create_typed_row.add_argument(
        "--skip-blob-diff",
        action="store_true",
        help="Skip blob/diff verification; useful while AppFlowy Web reports pending live rows",
    )
    create_typed_row.add_argument(
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

    upsert_typed_row = sub.add_parser("upsert-typed-row")
    upsert_typed_row.add_argument("--workspace-id", required=True)
    upsert_typed_row.add_argument("--database-id", required=True)
    upsert_typed_row.add_argument("--pre-hash")
    upsert_typed_row.add_argument(
        "--values-json",
        required=True,
        help="Human-friendly field values keyed by AppFlowy field name or id",
    )
    upsert_typed_row.add_argument("--document")
    upsert_typed_row.add_argument(
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

    view_configs = sub.add_parser(
        "view-configs",
        description=(
            "Read-only summary of database view settings from collab JSON: "
            "layout, filters, sorts, groups and field visibility/width."
        ),
    )
    view_configs.add_argument("--workspace-id", required=True)
    view_configs.add_argument("--database-id", required=True)

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

    search_tasks = sub.add_parser("search-tasks")
    search_tasks.add_argument("--workspace-id", required=True)
    search_tasks.add_argument("--database-id", required=True)
    search_tasks.add_argument("--description", required=True)
    search_tasks.add_argument("--mode", choices=["exact", "contains"], default="contains")
    search_tasks.add_argument("--case-sensitive", action="store_true")
    search_tasks.add_argument("--with-doc", action="store_true")

    create_task = sub.add_parser(
        "create-task",
        description="Create a browser-visible task row through the normal POST row route.",
    )
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

    update_task_by_name = sub.add_parser("update-task-by-name")
    update_task_by_name.add_argument("--workspace-id", required=True)
    update_task_by_name.add_argument("--database-id", required=True)
    update_task_by_name.add_argument("--description", required=True)
    update_task_by_name.add_argument("--new-description")
    update_task_by_name.add_argument("--status")
    update_task_by_name.add_argument("--match-mode", choices=["exact", "contains"], default="exact")
    update_task_by_name.add_argument("--case-sensitive", action="store_true")
    update_task_by_name.add_argument("--execute", action="store_true")

    move_task = sub.add_parser("move-task")
    move_task.add_argument("--workspace-id", required=True)
    move_task.add_argument("--database-id", required=True)
    move_task.add_argument("--task-key", required=True)
    move_task.add_argument("--status", required=True)
    move_task.add_argument("--execute", action="store_true")

    move_task_by_name = sub.add_parser("move-task-by-name")
    move_task_by_name.add_argument("--workspace-id", required=True)
    move_task_by_name.add_argument("--database-id", required=True)
    move_task_by_name.add_argument("--description", required=True)
    move_task_by_name.add_argument("--status", required=True)
    move_task_by_name.add_argument("--match-mode", choices=["exact", "contains"], default="exact")
    move_task_by_name.add_argument("--case-sensitive", action="store_true")
    move_task_by_name.add_argument("--execute", action="store_true")

    update_row_by_id = sub.add_parser("update-row-by-id")
    update_row_by_id.add_argument("--workspace-id", required=True)
    update_row_by_id.add_argument("--database-id", required=True)
    update_row_by_id.add_argument("--row-id", required=True)
    update_row_by_id.add_argument(
        "--values-json",
        required=True,
        help="Human-friendly field values keyed by AppFlowy field name or id",
    )
    update_row_by_id.add_argument("--execute", action="store_true")

    move_task_by_id = sub.add_parser("move-task-by-id")
    move_task_by_id.add_argument("--workspace-id", required=True)
    move_task_by_id.add_argument("--database-id", required=True)
    move_task_by_id.add_argument("--row-id", required=True)
    move_task_by_id.add_argument("--status", required=True)
    move_task_by_id.add_argument("--execute", action="store_true")

    delete_task = sub.add_parser("delete-task")
    delete_task.add_argument("--workspace-id", required=True)
    delete_task.add_argument("--database-id", required=True)
    delete_task.add_argument("--row-id", required=True)
    delete_task.add_argument("--execute", action="store_true")

    delete_task_by_name = sub.add_parser("delete-task-by-name")
    delete_task_by_name.add_argument("--workspace-id", required=True)
    delete_task_by_name.add_argument("--database-id", required=True)
    delete_task_by_name.add_argument("--description", required=True)
    delete_task_by_name.add_argument("--match-mode", choices=["exact", "contains"], default="exact")
    delete_task_by_name.add_argument("--case-sensitive", action="store_true")
    delete_task_by_name.add_argument("--execute", action="store_true")

    managed = sub.add_parser(
        "managed-task",
        description=(
            "Advanced/idempotent task_key upsert through pre_hash. "
            "Do not use for user-visible task creation; use create-task instead."
        ),
    )
    managed.add_argument("--workspace-id", required=True)
    managed.add_argument("--database-id", required=True)
    managed.add_argument("--task-key", required=True)
    managed.add_argument("--description")
    managed.add_argument("--status")
    managed.add_argument("--document")
    managed.add_argument(
        "--execute", action="store_true", help="Actually upsert it; default is dry-run"
    )

    managed_verified = sub.add_parser(
        "managed-task-verified",
        description=(
            "Advanced/idempotent task_key upsert with data-plane verification. "
            "May verify while AppFlowy Web Grid does not render fresh rows; "
            "use create-task for visible card creation."
        ),
    )
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
    if args.command == "doctor":
        print(to_json(_run_doctor(network=args.network)))
        return 0

    if args.command == "workflows":
        print(to_json(safe_workflows()))
        return 0

    if args.command == "setup-check":
        from appflowy_mcp_toolkit.collab.collab_delete import check_collab_helper_setup

        print(to_json(check_collab_helper_setup()))
        return 0

    # Template-center commands: read-only; handled in the shared client block below.

    with AppFlowyClient() as client:
        if args.command == "health":
            result: Any = client.health_check()
        elif args.command == "workspaces":
            result = client.list_workspaces(include_member_count=True, include_role=True)
        elif args.command == "server-info":
            result = client.get_server_info()
        elif args.command == "user-profile":
            result = client.get_user_profile()
        elif args.command == "user-workspace-info":
            result = client.get_user_workspace_info()
        elif args.command == "workspace-settings":
            result = client.get_workspace_settings(args.workspace_id)
        elif args.command == "workspace-members":
            result = client.list_workspace_members(args.workspace_id)
        elif args.command == "workspace-usage":
            result = client.get_workspace_usage(args.workspace_id)
        elif args.command == "publish-namespace":
            result = client.get_workspace_publish_namespace(args.workspace_id)
        elif args.command == "publish-default":
            result = client.get_workspace_publish_default(args.workspace_id)
        elif args.command == "published-pages":
            result = client.list_published_pages(args.workspace_id)
        elif args.command == "published-page-info":
            result = client.get_published_page_info(
                args.view_id,
                include_unpublished=args.include_unpublished,
            )
        elif args.command == "publish-page":
            visible_ids = (
                [v.strip() for v in args.visible_database_view_ids.split(",") if v.strip()]
                if args.visible_database_view_ids
                else None
            )
            result = client.publish_page(
                args.workspace_id,
                args.view_id,
                publish_name=args.publish_name,
                visible_database_view_ids=visible_ids,
                comments_enabled=args.comments_enabled,
                duplicate_enabled=args.duplicate_enabled,
                dry_run=not args.execute,
            )
        elif args.command == "unpublish-page":
            result = client.unpublish_page(
                args.workspace_id,
                args.view_id,
                dry_run=not args.execute,
            )
        elif args.command == "duplicate-published-page":
            result = client.duplicate_published_page(
                args.workspace_id,
                published_view_id=args.published_view_id,
                dest_view_id=args.dest_view_id,
                dry_run=not args.execute,
            )
        elif args.command == "instantiate-template":
            result = client.instantiate_template(
                args.workspace_id,
                template_view_id=args.template_view_id,
                dest_view_id=args.dest_view_id,
                dry_run=not args.execute,
            )
        elif args.command == "template-categories":
            result = client.list_template_categories(
                name_contains=args.name_contains,
                category_type=args.category_type,
            )
        elif args.command == "template-category":
            result = client.get_template_category(args.category_id)
        elif args.command == "template-creators":
            result = client.list_template_creators(name_contains=args.name_contains)
        elif args.command == "template-creator":
            result = client.get_template_creator(args.creator_id)
        elif args.command == "templates":
            result = client.list_templates(
                category_id=args.category_id,
                is_featured=args.is_featured,
                is_new_template=args.is_new_template,
                name_contains=args.name_contains,
            )
        elif args.command == "template":
            result = client.get_template(args.view_id)
        elif args.command == "template-homepage":
            result = client.get_template_homepage(per_count=args.per_count)
        elif args.command == "create-space":
            result = client.create_space(
                args.workspace_id,
                name=args.name,
                space_permission=args.space_permission,
                space_icon=args.space_icon,
                space_icon_color=args.space_icon_color,
                view_id=args.view_id,
                dry_run=not args.execute,
            )
        elif args.command == "update-space":
            result = client.update_space(
                args.workspace_id,
                args.view_id,
                name=args.name,
                space_permission=args.space_permission,
                space_icon=args.space_icon,
                space_icon_color=args.space_icon_color,
                dry_run=not args.execute,
            )
        elif args.command == "file-storage-usage":
            result = client.get_file_storage_usage(args.workspace_id)
        elif args.command == "file-storage-blobs":
            result = client.list_file_storage_blobs(args.workspace_id)
        elif args.command == "file-metadata":
            result = client.get_file_metadata(args.workspace_id, args.file_id)
        elif args.command == "file-metadata-v1":
            result = client.get_file_metadata_v1(
                args.workspace_id,
                args.parent_dir,
                args.file_id,
            )
        elif args.command == "upload-file-v1":
            result = client.upload_local_file_blob_v1(
                args.workspace_id,
                args.parent_dir,
                args.file_path,
                content_type=args.content_type,
                dry_run=not args.execute,
            )
        elif args.command == "download-file-v1":
            content_type, content = client.get_file_blob_v1(
                args.workspace_id,
                args.parent_dir,
                args.file_id,
            )
            Path(args.output).write_bytes(content)
            result = {
                "output": args.output,
                "content_type": content_type,
                "content_length": len(content),
            }
        elif args.command == "delete-file-v1":
            result = client.delete_file_blob_v1(
                args.workspace_id,
                args.parent_dir,
                args.file_id,
                dry_run=not args.execute,
            )
        elif args.command == "upload-media-file":
            result = client.upload_file_as_media(
                args.workspace_id,
                args.database_id,
                args.file_path,
                name=args.name,
                content_type=args.content_type,
                file_type=args.file_type,
                dry_run=not args.execute,
            )
        elif args.command == "folder":
            result = client.get_folder(
                args.workspace_id, depth=args.depth, root_view_id=args.root_view_id
            )
        elif args.command == "create-folder":
            result = client.create_folder_view(
                args.workspace_id,
                parent_view_id=args.parent_view_id,
                layout=args.layout,
                name=args.name,
                view_id=args.view_id,
                database_id=args.database_id,
                dry_run=not args.execute,
            )
        elif args.command == "page-view":
            result = client.get_page_view(args.workspace_id, args.view_id)
        elif args.command == "create-page":
            result = client.create_page_view(
                args.workspace_id,
                parent_view_id=args.parent_view_id,
                layout=args.layout,
                name=args.name,
                page_data=json.loads(args.page_data_json) if args.page_data_json else None,
                view_id=args.view_id,
                collab_id=args.collab_id,
                dry_run=not args.execute,
            )
        elif args.command == "update-page":
            result = client.update_page_view(
                args.workspace_id,
                args.view_id,
                name=args.name,
                icon=json.loads(args.icon_json) if args.icon_json else None,
                is_locked=args.is_locked,
                extra=json.loads(args.extra_json) if args.extra_json else None,
                dry_run=not args.execute,
            )
        elif args.command == "rename-page":
            result = client.update_page_name(
                args.workspace_id,
                args.view_id,
                name=args.name,
                dry_run=not args.execute,
            )
        elif args.command == "favorite-page":
            result = client.favorite_page_view(
                args.workspace_id,
                args.view_id,
                is_favorite=args.is_favorite,
                is_pinned=args.is_pinned,
                dry_run=not args.execute,
            )
        elif args.command == "remove-page-icon":
            result = client.remove_page_icon(
                args.workspace_id,
                args.view_id,
                dry_run=not args.execute,
            )
        elif args.command == "append-page-blocks":
            result = client.append_blocks_to_page(
                args.workspace_id,
                args.view_id,
                blocks=json.loads(args.blocks_json),
                dry_run=not args.execute,
            )
        elif args.command == "move-page":
            result = client.move_page_view(
                args.workspace_id,
                args.view_id,
                new_parent_view_id=args.new_parent_view_id,
                prev_view_id=args.prev_view_id,
                dry_run=not args.execute,
            )
        elif args.command == "reorder-favorite-page":
            result = client.reorder_favorite_page_view(
                args.workspace_id,
                args.view_id,
                prev_view_id=args.prev_view_id,
                dry_run=not args.execute,
            )
        elif args.command == "duplicate-page":
            result = client.duplicate_page_view(
                args.workspace_id,
                args.view_id,
                suffix=args.suffix,
                dry_run=not args.execute,
            )
        elif args.command == "create-page-database":
            result = client.create_page_database_view(
                args.workspace_id,
                args.view_id,
                layout=args.layout,
                name=args.name,
                dry_run=not args.execute,
            )
        elif args.command == "trash-page":
            result = client.move_page_view_to_trash(
                args.workspace_id,
                args.view_id,
                dry_run=not args.execute,
            )
        elif args.command == "restore-page":
            result = client.restore_page_view_from_trash(
                args.workspace_id,
                args.view_id,
                dry_run=not args.execute,
            )
        elif args.command == "delete-trash-page":
            result = client.delete_page_view_from_trash(
                args.workspace_id,
                args.view_id,
                dry_run=not args.execute,
            )
        elif args.command == "add-recent-pages":
            result = client.add_recent_pages(
                args.workspace_id,
                [part.strip() for part in args.view_ids.split(",") if part.strip()],
                dry_run=not args.execute,
            )
        elif args.command == "restore-all-pages":
            result = client.restore_all_pages_from_trash(
                args.workspace_id,
                dry_run=not args.execute,
            )
        elif args.command == "delete-all-trash-pages":
            result = client.delete_all_pages_from_trash(
                args.workspace_id,
                dry_run=not args.execute,
            )
        elif args.command == "recent":
            result = client.list_recent_views(args.workspace_id)
        elif args.command == "favorites":
            result = client.list_favorite_views(args.workspace_id)
        elif args.command == "trash":
            result = client.list_trash_views(args.workspace_id)
        elif args.command == "databases":
            result = client.list_databases(args.workspace_id)
        elif args.command == "fields":
            result = client.list_database_fields(args.workspace_id, args.database_id)
        elif args.command == "create-field":
            result = client.create_database_field(
                args.workspace_id,
                args.database_id,
                name=args.name,
                field_type=args.field_type,
                type_option_data=(
                    json.loads(args.type_option_data_json) if args.type_option_data_json else None
                ),
                dry_run=not args.execute,
            )
        elif args.command == "add-select-option":
            result = client.add_select_option_collab(
                args.workspace_id,
                args.database_id,
                field_name=args.field_name,
                name=args.name,
                color=args.color,
                option_id=args.option_id,
                view_id=args.view_id,
                dry_run=not args.execute,
            )
        elif args.command == "rename-select-option":
            result = client.rename_select_option_collab(
                args.workspace_id,
                args.database_id,
                field_name=args.field_name,
                option_id=args.option_id,
                option_name=args.option_name,
                new_name=args.new_name,
                dry_run=not args.execute,
            )
        elif args.command == "hide-select-option":
            result = client.set_select_option_visibility_collab(
                args.workspace_id,
                args.database_id,
                field_name=args.field_name,
                option_id=args.option_id,
                option_name=args.option_name,
                visible=False,
                view_id=args.view_id,
                dry_run=not args.execute,
            )
        elif args.command == "show-select-option":
            result = client.set_select_option_visibility_collab(
                args.workspace_id,
                args.database_id,
                field_name=args.field_name,
                option_id=args.option_id,
                option_name=args.option_name,
                visible=True,
                view_id=args.view_id,
                dry_run=not args.execute,
            )
        elif args.command == "rows":
            result = client.list_database_row_ids(args.workspace_id, args.database_id)
        elif args.command == "updated-rows":
            result = client.list_updated_database_rows(
                args.workspace_id,
                args.database_id,
                after=args.after,
            )
        elif args.command == "quick-notes":
            result = client.list_quick_notes(
                args.workspace_id,
                search_term=args.search_term,
                offset=args.offset,
                limit=args.limit,
            )
        elif args.command == "create-quick-note":
            result = client.create_quick_note(
                args.workspace_id,
                data=json.loads(args.data_json) if args.data_json is not None else None,
                dry_run=not args.execute,
            )
        elif args.command == "update-quick-note":
            result = client.update_quick_note(
                args.workspace_id,
                args.quick_note_id,
                data=json.loads(args.data_json),
                dry_run=not args.execute,
            )
        elif args.command == "delete-quick-note":
            result = client.delete_quick_note(
                args.workspace_id,
                args.quick_note_id,
                dry_run=not args.execute,
            )
        elif args.command == "search":
            result = client.search_documents(
                args.workspace_id,
                args.query,
                limit=args.limit,
                preview_size=args.preview_size,
                score=args.score,
            )
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
        elif args.command == "create-typed-row":
            result = client.create_typed_database_row_verified(
                args.workspace_id,
                args.database_id,
                values=json.loads(args.values_json),
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
        elif args.command == "upsert-typed-row":
            result = client.upsert_typed_database_row(
                args.workspace_id,
                args.database_id,
                pre_hash=args.pre_hash,
                values=json.loads(args.values_json),
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
        elif args.command == "view-configs":
            result = client.get_database_view_configs(args.workspace_id, args.database_id)
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
        elif args.command == "search-tasks":
            result = client.search_tasks_by_description(
                args.workspace_id,
                args.database_id,
                args.description,
                mode=args.mode,
                case_sensitive=args.case_sensitive,
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
        elif args.command == "update-task-by-name":
            result = client.update_task_by_description(
                args.workspace_id,
                args.database_id,
                args.description,
                new_description=args.new_description,
                status=args.status,
                match_mode=args.match_mode,
                case_sensitive=args.case_sensitive,
                dry_run=not args.execute,
            )
        elif args.command == "move-task":
            result = client.move_task(
                args.workspace_id,
                args.database_id,
                task_key=args.task_key,
                status=args.status,
                dry_run=not args.execute,
            )
        elif args.command == "move-task-by-name":
            result = client.move_task_by_description(
                args.workspace_id,
                args.database_id,
                args.description,
                status=args.status,
                match_mode=args.match_mode,
                case_sensitive=args.case_sensitive,
                dry_run=not args.execute,
            )
        elif args.command == "update-row-by-id":
            result = client.update_database_row_by_id_collab(
                args.workspace_id,
                args.database_id,
                args.row_id,
                values=json.loads(args.values_json),
                dry_run=not args.execute,
            )
        elif args.command == "move-task-by-id":
            result = client.move_task_by_row_id(
                args.workspace_id,
                args.database_id,
                args.row_id,
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
        elif args.command == "delete-task-by-name":
            result = client.delete_task_by_description(
                args.workspace_id,
                args.database_id,
                args.description,
                match_mode=args.match_mode,
                case_sensitive=args.case_sensitive,
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
