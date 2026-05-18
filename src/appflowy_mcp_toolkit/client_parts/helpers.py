from __future__ import annotations

from typing import Any

from appflowy_mcp_toolkit.errors import AppFlowyError


def _summarize_collab(
    raw: Any,
    *,
    workspace_id: str,
    object_id: str,
    collab_type: str,
    include_raw: bool = False,
) -> dict[str, Any]:
    """Return a safe high-level summary of a raw collab JSON document.

    Emits shape/key counts and metadata without the raw body unless
    ``include_raw=True`` is explicitly requested.
    """
    summary: dict[str, Any] = {
        "diagnostic": True,
        "workspace_id": workspace_id,
        "object_id": object_id,
        "collab_type": collab_type,
        "raw_risk_note": (
            "Full raw collab JSON may contain large internal Yjs state. "
            "Pass include_raw=True only when you need the complete document body."
        ),
    }
    if isinstance(raw, dict):
        summary["top_level_keys"] = list(raw.keys())
        summary["top_level_key_count"] = len(raw)
        # Shallow size hints for common well-known sub-keys
        for key in ("views", "rows", "fields", "cells", "blocks", "children"):
            if key in raw:
                val = raw[key]
                if isinstance(val, (dict, list)):
                    summary[f"{key}_count"] = len(val)
    elif isinstance(raw, list):
        summary["top_level_type"] = "list"
        summary["item_count"] = len(raw)
    else:
        summary["top_level_type"] = type(raw).__name__

    if include_raw:
        summary["raw"] = raw

    return summary


def _collab_type_int(collab_type: str | int) -> int:
    """Resolve a collab type name, integer, or decimal numeric string to the
    integer the server requires.

    The AppFlowy Cloud ``/json`` endpoint deserialises ``collab_type`` as an
    integer.  Passing a string such as ``"Database"`` results in a 400 error.

    Accepted forms:
    - ``int``: forwarded as-is (e.g. ``1``)
    - decimal numeric string: parsed as int (e.g. ``"1"`` → ``1``)
    - known name string: mapped to int (e.g. ``"Database"`` → ``1``)

    Known mappings (from ``collab_entity::CollabType``):
    ``Document=0, Database=1, WorkspaceDatabase=2, Folder=3,
    DatabaseRow=4, UserAwareness=5``.
    """
    if isinstance(collab_type, int):
        return collab_type
    if collab_type.isdigit():
        return int(collab_type)
    _COLLAB_TYPE_MAP: dict[str, int] = {
        "Document": 0,
        "Database": 1,
        "WorkspaceDatabase": 2,
        "Folder": 3,
        "DatabaseRow": 4,
        "UserAwareness": 5,
    }
    resolved = _COLLAB_TYPE_MAP.get(collab_type)
    if resolved is None:
        raise AppFlowyError(
            f"Unknown collab_type name {collab_type!r}. "
            f"Pass an integer, a decimal string, or one of: {list(_COLLAB_TYPE_MAP)}"
        )
    return resolved


def _extract_row_id(create_result: dict[str, Any]) -> str | None:
    data = create_result.get("data")
    if isinstance(data, str) and data:
        return data
    if isinstance(data, dict):
        for key in ("id", "row_id"):
            value = data.get(key)
            if isinstance(value, str) and value:
                return value
    for key in ("id", "row_id"):
        value = create_result.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _iter_database_view_items(collab: Any) -> list[tuple[str, dict[str, Any]]]:
    """Return database view items from all observed collab JSON shapes."""
    if not isinstance(collab, dict):
        return []

    def _views_to_items(views: Any) -> list[tuple[str, dict[str, Any]]]:
        if not isinstance(views, dict):
            return []
        out: list[tuple[str, dict[str, Any]]] = []
        for view_id, view_data in views.items():
            if isinstance(view_data, dict):
                out.append((str(view_id), view_data))
        return out

    nested_collab = collab.get("collab")
    if isinstance(nested_collab, dict):
        db = nested_collab.get("database")
        if isinstance(db, dict):
            results = _views_to_items(db.get("views"))
            if results:
                return results

    results = _views_to_items(collab.get("views"))
    if results:
        return results

    for key in ("database_inline_views", "inline_views"):
        results = _views_to_items(collab.get(key))
        if results:
            return results

    return []


def _extract_row_orders(collab: Any) -> list[dict[str, Any]]:
    """Extract per-view row orders from a database collab JSON payload.

    The AppFlowy Cloud ``/json`` endpoint returns (after ``_extract_data``) a
    dict whose shape depends on the server version:

    **Observed AppFlowy response shape** (2026-05):

    .. code-block:: json

        {"collab": {"database": {"views": {"<view_id>": {"row_orders": [...]}}}}}

    **Flat fixture shape** (used in unit tests / earlier schema):

    .. code-block:: json

        {"views": {"<view_id>": {"row_orders": [...]}}}

    **Inline-views fallback**:

    .. code-block:: json

        {"database_inline_views": {"<view_id>": {"row_orders": [...]}}}

    This helper tries all known locations and returns the first non-empty match.
    ``row_orders`` entries may be plain strings or ``{"id": "..."}`` dicts;
    both are normalised to strings.

    Returns a list of dicts::

        [{"view_id": "<id>", "row_orders": ["<row_id>", ...]}, ...]
    """
    return [
        {"view_id": view_id, "row_orders": _coerce_row_orders(view_data.get("row_orders"))}
        for view_id, view_data in _iter_database_view_items(collab)
    ]


def _extract_view_configs(collab: Any) -> list[dict[str, Any]]:
    """Extract normalized database view configuration from collab JSON.

    The raw AppFlowy view object contains many fields. This helper keeps the
    configuration surface relevant to humans: layout, layout settings, filters,
    sorts, group settings, field settings, field order and row count.
    """
    out: list[dict[str, Any]] = []
    for view_id, view_data in _iter_database_view_items(collab):
        row_orders = _coerce_row_orders(view_data.get("row_orders"))
        field_orders = _coerce_field_orders(view_data.get("field_orders"))
        out.append(
            {
                "view_id": view_id,
                "name": view_data.get("name"),
                "database_id": view_data.get("database_id"),
                "layout": view_data.get("layout"),
                "layout_name": _layout_name(view_data.get("layout")),
                "is_inline": view_data.get("is_inline"),
                "layout_settings": _dict_or_empty(view_data.get("layout_settings")),
                "filters": _list_or_empty(view_data.get("filters")),
                "sorts": _list_or_empty(view_data.get("sorts")),
                "group_settings": _normalise_group_settings(view_data.get("group_settings")),
                "field_settings": _normalise_field_settings(view_data.get("field_settings")),
                "field_orders": field_orders,
                "field_order_count": len(field_orders),
                "row_order_count": len(row_orders),
                "created_at": view_data.get("created_at"),
                "modified_at": view_data.get("modified_at"),
            }
        )
    return out


def _coerce_row_orders(raw: Any) -> list[str]:
    """Normalise row_orders to a flat list of row-id strings.

    AppFlowy may encode row_orders as:
    - a list of strings: ["row_id_1", ...]
    - a list of dicts: [{"id": "row_id_1"}, ...]
    - absent / other: return []
    """
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            row_id = item.get("id")
            if isinstance(row_id, str):
                out.append(row_id)
    return out


def _coerce_field_orders(raw: Any) -> list[str]:
    """Normalise field_orders to a flat list of field-id strings."""
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            field_id = item.get("id") or item.get("field_id")
            if isinstance(field_id, str):
                out.append(field_id)
    return out


def _dict_or_empty(raw: Any) -> dict[str, Any]:
    return raw if isinstance(raw, dict) else {}


def _list_or_empty(raw: Any) -> list[Any]:
    return raw if isinstance(raw, list) else []


def _layout_name(raw: Any) -> str | None:
    layout_id: int | None = None
    if isinstance(raw, int):
        layout_id = raw
    elif isinstance(raw, str) and raw.isdigit():
        layout_id = int(raw)
    if layout_id is None:
        return None
    return {0: "Grid", 1: "Board", 2: "Calendar"}.get(layout_id)


def _normalise_field_settings(raw: Any) -> dict[str, dict[str, Any]]:
    """Return field settings keyed by field id with common knobs surfaced."""
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for field_id, settings in raw.items():
        if not isinstance(settings, dict):
            continue
        out[str(field_id)] = {
            "visibility": settings.get("visibility"),
            "width": settings.get("width"),
            "wrap_cell_content": settings.get("wrap_cell_content", settings.get("wrap")),
            "raw": settings,
        }
    return out


def _normalise_group_settings(raw: Any) -> list[dict[str, Any]]:
    """Return board/group settings with group ids and visibility surfaced."""
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for setting in raw:
        if not isinstance(setting, dict):
            continue
        groups = []
        raw_groups = setting.get("groups")
        if isinstance(raw_groups, list):
            for group in raw_groups:
                if isinstance(group, dict):
                    groups.append(
                        {
                            "id": group.get("id"),
                            "visible": group.get("visible"),
                            "raw": group,
                        }
                    )
                elif isinstance(group, str):
                    groups.append({"id": group, "visible": None, "raw": group})
        out.append(
            {
                "id": setting.get("id"),
                "field_id": setting.get("field_id"),
                "field_type": setting.get("ty", setting.get("field_type")),
                "content": setting.get("content"),
                "groups": groups,
                "raw": setting,
            }
        )
    return out
