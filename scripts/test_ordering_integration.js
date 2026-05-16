#!/usr/bin/env node
/**
 * Offline integration tests for reorder_row and reorder_column helper operations.
 *
 * Builds synthetic Yjs docs in-process, serialises them to doc_state bytes,
 * pipes each payload into the actual yjs_helper.js subprocess, and asserts
 * the resulting order is correct.
 *
 * No network access. No AppFlowy credentials required.
 * Run: node scripts/test_ordering_integration.js
 * Exit 0 = all pass; exit 1 = at least one failure.
 */

"use strict";

const path = require("path");
const { execSync } = require("child_process");

const Y = require(path.join(__dirname, "../src/appflowy_mcp_toolkit/collab/node_modules/yjs"));
const HELPER = path.join(__dirname, "../src/appflowy_mcp_toolkit/collab/yjs_helper.js");

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function invokeHelper(payload) {
  const out = execSync(`node ${HELPER}`, { input: JSON.stringify(payload), encoding: "utf8" });
  return JSON.parse(out);
}

function rowOrder(docState, viewId) {
  const doc = new Y.Doc();
  Y.applyUpdate(doc, new Uint8Array(docState));
  return doc
    .getMap("data")
    .get("database")
    .get("views")
    .get(viewId)
    .get("row_orders")
    .toArray()
    .map((m) => (m instanceof Y.Map ? m.get("id") : m.id));
}

function columnOrder(docState, viewId, fieldId) {
  const doc = new Y.Doc();
  Y.applyUpdate(doc, new Uint8Array(docState));
  return doc
    .getMap("data")
    .get("database")
    .get("views")
    .get(viewId)
    .get("groups")
    .toArray()
    .find((g) => g instanceof Y.Map && g.get("field_id") === fieldId)
    .get("groups")
    .toArray()
    .map((m) => (m instanceof Y.Map ? m.get("id") : m.id));
}

function applyDelta(docState, deltaUpdate) {
  const doc = new Y.Doc();
  Y.applyUpdate(doc, new Uint8Array(docState));
  Y.applyUpdate(doc, new Uint8Array(deltaUpdate));
  return Array.from(Y.encodeStateAsUpdate(doc));
}

function buildRowDoc(viewId, rowIds) {
  const doc = new Y.Doc();
  const root = doc.getMap("data");
  const db = new Y.Map();
  root.set("database", db);
  const views = new Y.Map();
  db.set("views", views);
  const view = new Y.Map();
  views.set(viewId, view);
  const ro = new Y.Array();
  view.set("row_orders", ro);
  const maps = rowIds.map((id) => {
    const m = new Y.Map();
    m.set("id", id);
    m.set("height", 60);
    return m;
  });
  ro.insert(0, maps);
  return Array.from(Y.encodeStateAsUpdate(doc));
}

function buildColumnDoc(viewId, fieldId, groupIds) {
  const doc = new Y.Doc();
  const root = doc.getMap("data");
  const db = new Y.Map();
  root.set("database", db);
  const views = new Y.Map();
  db.set("views", views);
  const view = new Y.Map();
  views.set(viewId, view);
  const groups = new Y.Array();
  view.set("groups", groups);
  // top-level group entry for this field
  const fieldGroup = new Y.Map();
  fieldGroup.set("field_id", fieldId);
  fieldGroup.set("ty", 3);
  const childGroups = new Y.Array();
  const children = groupIds.map((id) => {
    const m = new Y.Map();
    m.set("id", id);
    m.set("visible", true);
    return m;
  });
  if (children.length > 0) childGroups.insert(0, children);
  fieldGroup.set("groups", childGroups);
  groups.insert(0, [fieldGroup]);
  return Array.from(Y.encodeStateAsUpdate(doc));
}

// ---------------------------------------------------------------------------
// Test runner
// ---------------------------------------------------------------------------

let passed = 0;
let failed = 0;

function assert(condition, msg) {
  if (!condition) {
    console.error("  FAIL:", msg);
    failed++;
  } else {
    console.log("  pass:", msg);
    passed++;
  }
}

function assertEqual(actual, expected, msg) {
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  if (a !== e) {
    console.error(`  FAIL: ${msg}\n    actual:   ${a}\n    expected: ${e}`);
    failed++;
  } else {
    console.log("  pass:", msg);
    passed++;
  }
}

// ---------------------------------------------------------------------------
// Row reorder tests
// ---------------------------------------------------------------------------

console.log("\n=== reorder_row ===");

{
  // Move first row to end (before_row_id: null) — the exact failing case
  const viewId = "view1";
  const docState = buildRowDoc(viewId, ["a", "b", "c"]);
  const result = invokeHelper({ operation: "reorder_row", view_id: viewId, row_id: "a", before_row_id: null, doc_state: docState });
  assert(result.ok === true, "append: ok");
  assert(result.moved === true, "append: moved");
  assertEqual(result.from_index, 0, "append: from_index");
  assertEqual(result.to_index, 2, "append: to_index");
  const finalState = applyDelta(docState, result.delta_update);
  assertEqual(rowOrder(finalState, viewId), ["b", "c", "a"], "append: final order [b,c,a]");
}

{
  // Move last row to first position
  const viewId = "view2";
  const docState = buildRowDoc(viewId, ["a", "b", "c"]);
  const result = invokeHelper({ operation: "reorder_row", view_id: viewId, row_id: "c", before_row_id: "a", doc_state: docState });
  assert(result.ok === true, "move-to-front: ok");
  assert(result.moved === true, "move-to-front: moved");
  const finalState = applyDelta(docState, result.delta_update);
  assertEqual(rowOrder(finalState, viewId), ["c", "a", "b"], "move-to-front: final order [c,a,b]");
}

{
  // Move middle row before last
  const viewId = "view3";
  const docState = buildRowDoc(viewId, ["a", "b", "c"]);
  const result = invokeHelper({ operation: "reorder_row", view_id: viewId, row_id: "a", before_row_id: "c", doc_state: docState });
  assert(result.ok === true, "move-mid: ok");
  const finalState = applyDelta(docState, result.delta_update);
  assertEqual(rowOrder(finalState, viewId), ["b", "a", "c"], "move-mid: final order [b,a,c]");
}

{
  // No-op: row already at target position
  const viewId = "view4";
  const docState = buildRowDoc(viewId, ["a", "b", "c"]);
  const result = invokeHelper({ operation: "reorder_row", view_id: viewId, row_id: "a", before_row_id: "b", doc_state: docState });
  assert(result.ok === true, "noop: ok");
  assert(result.moved === false, "noop: moved=false");
  // delta_update may be a non-empty state-vector header even for no-op; just
  // verify moved=false rather than asserting zero bytes.
  assert(Array.isArray(result.delta_update), "noop: delta_update is array");
}

{
  // Error: row_id not found
  const viewId = "view5";
  const docState = buildRowDoc(viewId, ["a", "b"]);
  const { stdout: out1 } = require("child_process").spawnSync("node", [HELPER], {
    input: JSON.stringify({ operation: "reorder_row", view_id: viewId, row_id: "MISSING", before_row_id: null, doc_state: docState }),
    encoding: "utf8",
  });
  const result = JSON.parse(out1);
  assert(result.ok === false, "missing-row: ok=false");
  assert(result.error.includes("MISSING"), "missing-row: error mentions id");
}

{
  // Error: before_row_id not found
  const viewId = "view6";
  const docState = buildRowDoc(viewId, ["a", "b"]);
  const { stdout: out2 } = require("child_process").spawnSync("node", [HELPER], {
    input: JSON.stringify({ operation: "reorder_row", view_id: viewId, row_id: "a", before_row_id: "GHOST", doc_state: docState }),
    encoding: "utf8",
  });
  const result = JSON.parse(out2);
  assert(result.ok === false, "bad-before: ok=false");
}

// ---------------------------------------------------------------------------
// Column reorder tests
// ---------------------------------------------------------------------------

console.log("\n=== reorder_column ===");

{
  // Move first column to end
  const viewId = "board1";
  const fieldId = "f-status";
  const docState = buildColumnDoc(viewId, fieldId, ["todo", "in-progress", "done"]);
  const result = invokeHelper({ operation: "reorder_column", view_id: viewId, field_id: fieldId, group_id: "todo", before_group_id: null, doc_state: docState });
  assert(result.ok === true, "col-append: ok");
  assert(result.moved === true, "col-append: moved");
  const finalState = applyDelta(docState, result.delta_update);
  assertEqual(columnOrder(finalState, viewId, fieldId), ["in-progress", "done", "todo"], "col-append: final order");
}

{
  // Move last column to front
  const viewId = "board2";
  const fieldId = "f-status";
  const docState = buildColumnDoc(viewId, fieldId, ["todo", "in-progress", "done"]);
  const result = invokeHelper({ operation: "reorder_column", view_id: viewId, field_id: fieldId, group_id: "done", before_group_id: "todo", doc_state: docState });
  assert(result.ok === true, "col-to-front: ok");
  const finalState = applyDelta(docState, result.delta_update);
  assertEqual(columnOrder(finalState, viewId, fieldId), ["done", "todo", "in-progress"], "col-to-front: final order");
}

{
  // Move middle column before last
  const viewId = "board3";
  const fieldId = "f-status";
  const docState = buildColumnDoc(viewId, fieldId, ["todo", "in-progress", "done"]);
  const result = invokeHelper({ operation: "reorder_column", view_id: viewId, field_id: fieldId, group_id: "in-progress", before_group_id: "done", doc_state: docState });
  assert(result.ok === true, "col-mid: ok");
  const finalState = applyDelta(docState, result.delta_update);
  // in-progress was already before done — no-op
  assert(result.moved === false, "col-mid-already-in-place: moved=false");
}

{
  // Error: group_id not found
  const viewId = "board4";
  const fieldId = "f-status";
  const docState = buildColumnDoc(viewId, fieldId, ["todo", "done"]);
  const { stdout: out3 } = require("child_process").spawnSync("node", [HELPER], {
    input: JSON.stringify({ operation: "reorder_column", view_id: viewId, field_id: fieldId, group_id: "MISSING", before_group_id: null, doc_state: docState }),
    encoding: "utf8",
  });
  const result = JSON.parse(out3);
  assert(result.ok === false, "missing-col: ok=false");
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------

console.log(`\n${passed + failed} tests: ${passed} passed, ${failed} failed`);
if (failed > 0) process.exit(1);
