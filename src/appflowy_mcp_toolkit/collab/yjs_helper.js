/**
 * AppFlowy collab row-delete helper for the Python toolkit.
 *
 * Protocol: reads one JSON object from stdin, writes one JSON object to stdout.
 * No network access. No tokens. Pure in-memory Yjs mutation.
 *
 * License: MIT
 * Runtime: Node.js 18+
 * Dependencies: yjs (MIT) — no AGPL code.
 *
 * Input (JSON from stdin):
 *   {
 *     "doc_state": [<byte>, ...],   // lib0-v1 bytes from AppFlowy Cloud binary collab
 *     "row_id":    "<uuid>"         // row to remove from every view's row_orders
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

    const { doc_state, row_id } = input;
    if (!Array.isArray(doc_state) || typeof row_id !== "string") {
      process.stdout.write(
        JSON.stringify({ ok: false, error: "Input must have doc_state (array) and row_id (string)" })
      );
      process.exit(1);
    }

    let result;
    try {
      result = deleteRowFromCollab(new Uint8Array(doc_state), row_id);
    } catch (e) {
      process.stdout.write(JSON.stringify({ ok: false, error: e.message }));
      process.exit(1);
    }

    process.stdout.write(
      JSON.stringify({
        ok: true,
        row_found: result.rowFound,
        views_affected: result.affectedViews,
        view_row_counts: result.viewRowCounts,
        delta_update: Array.from(result.deltaUpdate),
      })
    );
  });
}

main();
