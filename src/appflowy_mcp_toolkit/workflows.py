from __future__ import annotations

from typing import Any


def safe_workflows() -> dict[str, Any]:
    """Return safe operating paths for agents using the toolkit."""
    return {
        "principles": [
            "Use task-facing helpers before raw row or collab tools.",
            "Use browser-verified create_task for new visible task cards.",
            "Resolve ambiguous human names with search_tasks before mutating rows.",
            "Keep real writes opt-in; collab/Yjs writes need an extra opt-in flag.",
            "Do not treat low-level page block append as polished Markdown editing.",
        ],
        "task_cards": {
            "new_visible_card": {
                "preferred": "create-task / appflowy_create_task",
                "why": (
                    "Uses AppFlowy's normal row-create route and is browser-tested "
                    "for Grid visibility."
                ),
            },
            "existing_or_manual_card": {
                "preferred": [
                    "search-tasks / appflowy_search_tasks",
                    "move-task-by-id / appflowy_move_task_by_id",
                    "update-row-by-id / appflowy_update_database_row_by_id",
                ],
                "why": (
                    "Manual rows already have row_id values; pre_hash upsert cannot "
                    "target arbitrary existing rows."
                ),
            },
            "human_named_card": {
                "preferred": [
                    "search-tasks with exact or contains mode",
                    "use by-name helpers only when one match exists",
                ],
                "why": "Name-based helpers refuse ambiguous matches instead of guessing.",
            },
            "idempotent_agent_card": {
                "advanced": [
                    "managed-task / appflowy_upsert_managed_task",
                    "managed-task-verified / appflowy_upsert_verified_managed_task",
                ],
                "warning": "Use only when a stable task_key/pre_hash workflow is intentional.",
            },
        },
        "collab_writes": {
            "row_delete": (
                "delete-task / appflowy_delete_task, with APPFLOWY_ALLOW_WRITES=true "
                "and APPFLOWY_ALLOW_COLLAB_WRITES=true for live execution."
            ),
            "row_reorder": (
                "row/card reorder tools require the same write and collab write opt-in flags."
            ),
            "board_column_reorder": (
                "board column reorder tools require the same write and collab write opt-in flags."
            ),
        },
        "page_documents": {
            "page_view_organization": (
                "create/rename/move/trash page-view tools are available with normal write gates."
            ),
            "document_markdown": (
                "append-page-markdown converts Markdown (paragraphs, headings, "
                "bulleted/numbered lists, blockquotes) to AppFlowy blocks and appends "
                "to an existing page. Full inline formatting is plain text only (backlog). "
                "Fetch/replace/block-level editing is not supported."
            ),
            "raw_append_blocks": (
                "append-page-blocks is a low-level primitive; prefer append-page-markdown "
                "for human-readable Markdown input."
            ),
            "templates": (
                "template-center category/template/creator discovery is read-only; "
                "instantiate-template duplicates a published template/page into a workspace view."
            ),
            "publishing": (
                "publish namespace/default/list/info metadata reads are available; "
                "publish/unpublish writes are supported with APPFLOWY_ALLOW_WRITES "
                "and APPFLOWY_ALLOW_PUBLISH_WRITES gates."
            ),
        },
        "unsupported": [
            "publishing/public sharing mutations",
            "member, invite, access, and admin mutations",
            "template instantiation as an end-to-end workflow",
            "import/export and migrations",
            "comments, reminders, live cursors, and presence",
            "AppFlowy AI/chat automation",
            "broad generic collab/Yjs mutation tools",
        ],
    }
