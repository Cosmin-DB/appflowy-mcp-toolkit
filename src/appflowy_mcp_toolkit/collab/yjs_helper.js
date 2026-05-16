/**
 * AppFlowy collab mutation helper for the Python toolkit.
 *
 * Protocol: reads one JSON object from stdin, writes one JSON object to stdout.
 * No network access. No tokens. Pure in-memory Yjs mutation.
 *
 * License: MIT
 * Runtime: Node.js 18+
 * Dependencies: yjs (MIT) — no AGPL code.
 *
 * Delete input (JSON from stdin, legacy default):
 *   {
 *     "operation": "delete_row",    // optional; default
 *     "doc_state": [<byte>, ...],   // lib0-v1 bytes from AppFlowy Cloud binary collab
 *     "row_id":    "<uuid>"         // row to remove from every view's row_orders
 *   }
 *
 * DatabaseRow update input:
 *   {
 *     "operation": "update_row_cells",
 *     "doc_state": [<byte>, ...],
 *     "cells": {
 *       "<field_id>": {"field_type": 3, "data": "<internal AppFlowy cell payload>"}
 *     }
 *   }
 *
 * Output (JSON to stdout):
 *   {
 *     "ok":              true,
 *     "row_found":       true | false,
 *     "views_affected":  ["<view_id>", ...],
 *     "view_row_counts": { "<view_id>": {"before": N, "after": N}, ... },
 *     "delta_update":    [<byte>, ...]   // incremental lib0-v1 update ready for web-update
 *   }
 *
 *   On error:
 *   { "ok": false, "error": "<message>" }
 */

"use strict";

const path = require("path");

// Resolve yjs relative to this file so the helper works from any cwd.
const Y = require(path.join(__dirname, "node_modules", "yjs"));

function getRowId(item) {
  if (item instanceof Y.Map) return item.get("id");
  if (item && typeof item === "object") return item.id; // plain object (live collab shape)
  if (typeof item === "string") return item;
  return undefined;
}

function deleteRowFromCollab(docStateBytes, targetRowId) {
  const doc = new Y.Doc();
  Y.applyUpdate(doc, docStateBytes);

  const svBefore = Y.encodeStateVector(doc);

  const root = doc.getMap("data");
  const database = root.get("database");
  if (!(database instanceof Y.Map)) {
    throw new Error("data.database not found or not a YMap in collab doc");
  }
  const views = database.get("views");
  if (!(views instanceof Y.Map)) {
    throw new Error("data.database.views not found or not a YMap in collab doc");
  }

  const viewRowCounts = {};
  const affectedViews = [];

  // Capture before-counts
  for (const [viewId, viewData] of views.entries()) {
    if (!(viewData instanceof Y.Map)) continue;
    const ro = viewData.get("row_orders");
    if (!(ro instanceof Y.Array)) continue;
    viewRowCounts[viewId] = { before: ro.length, after: ro.length };
  }

  // Mutation in one transaction
  doc.transact(() => {
    for (const [viewId, viewData] of views.entries()) {
      if (!(viewData instanceof Y.Map)) continue;
      const ro = viewData.get("row_orders");
      if (!(ro instanceof Y.Array)) continue;
      const items = ro.toArray();
      for (let i = items.length - 1; i >= 0; i--) {
        if (getRowId(items[i]) === targetRowId) {
          ro.delete(i, 1);
          affectedViews.push(viewId);
        }
      }
    }
  });

  // Capture after-counts
  for (const [viewId, viewData] of views.entries()) {
    if (!(viewData instanceof Y.Map)) continue;
    const ro = viewData.get("row_orders");
    if (!(ro instanceof Y.Array)) continue;
    if (viewRowCounts[viewId]) {
      viewRowCounts[viewId].after = ro.length;
    }
  }

  const deltaUpdate = Y.encodeStateAsUpdate(doc, svBefore);

  return {
    rowFound: affectedViews.length > 0,
    affectedViews: [...new Set(affectedViews)],
    viewRowCounts,
    deltaUpdate,
  };
}

function ensureMap(parent, key) {
  let value = parent.get(key);
  if (!(value instanceof Y.Map)) {
    value = new Y.Map();
    parent.set(key, value);
  }
  return value;
}

function updateDatabaseRowCells(docStateBytes, cellUpdates) {
  const doc = new Y.Doc();
  Y.applyUpdate(doc, docStateBytes);

  const svBefore = Y.encodeStateVector(doc);
  const root = doc.getMap("data");
  const rowData = root.get("data");
  if (!(rowData instanceof Y.Map)) {
    throw new Error("data.data not found or not a YMap in DatabaseRow collab doc");
  }
  const cells = ensureMap(rowData, "cells");
  const now = Date.now();
  const updatedFields = [];

  doc.transact(() => {
    for (const [fieldId, update] of Object.entries(cellUpdates)) {
      if (!fieldId || !update || typeof update !== "object" || !("data" in update)) {
        throw new Error("Each cell update must be keyed by field id and include data");
      }
      let cell = cells.get(fieldId);
      if (!(cell instanceof Y.Map)) {
        cell = new Y.Map();
        cell.set("created_at", now);
        cell.set("field_type", Number.isInteger(update.field_type) ? update.field_type : 0);
        cells.set(fieldId, cell);
      } else if (Number.isInteger(update.field_type) && cell.get("field_type") === undefined) {
        cell.set("field_type", update.field_type);
      }
      cell.set("data", update.data);
      cell.set("last_modified", now);
      updatedFields.push(fieldId);
    }
    rowData.set("last_modified", now);
  });

  const deltaUpdate = Y.encodeStateAsUpdate(doc, svBefore);
  return {
    updatedFields,
    deltaUpdate,
  };
}

function main() {
  const chunks = [];
  process.stdin.on("data", (c) => chunks.push(c));
  process.stdin.on("end", () => {
    let input;
    try {
      input = JSON.parse(Buffer.concat(chunks).toString("utf8"));
    } catch (e) {
      process.stdout.write(JSON.stringify({ ok: false, error: "JSON parse error: " + e.message }));
      process.exit(1);
    }

    const operation = input.operation || "delete_row";
    const { doc_state } = input;
    if (!Array.isArray(doc_state)) {
      process.stdout.write(JSON.stringify({ ok: false, error: "Input must have doc_state (array)" }));
      process.exit(1);
    }

    let result;
    try {
      if (operation === "delete_row") {
        if (typeof input.row_id !== "string") {
          throw new Error("delete_row input must include row_id (string)");
        }
        result = deleteRowFromCollab(new Uint8Array(doc_state), input.row_id);
      } else if (operation === "update_row_cells") {
        if (!input.cells || typeof input.cells !== "object" || Array.isArray(input.cells)) {
          throw new Error("update_row_cells input must include cells (object)");
        }
        result = updateDatabaseRowCells(new Uint8Array(doc_state), input.cells);
      } else {
        throw new Error("Unsupported operation: " + operation);
      }
    } catch (e) {
      process.stdout.write(JSON.stringify({ ok: false, error: e.message }));
      process.exit(1);
    }

    if (operation === "delete_row") {
      process.stdout.write(
        JSON.stringify({
          ok: true,
          row_found: result.rowFound,
          views_affected: result.affectedViews,
          view_row_counts: result.viewRowCounts,
          delta_update: Array.from(result.deltaUpdate),
        })
      );
    } else {
      process.stdout.write(
        JSON.stringify({
          ok: true,
          updated_fields: result.updatedFields,
          delta_update: Array.from(result.deltaUpdate),
        })
      );
    }
  });
}

main();
