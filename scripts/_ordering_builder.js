#!/usr/bin/env node
/**
 * Yjs doc builder used by test_ordering_integration.py.
 * Called as: node scripts/_ordering_builder.js <cmd> <json-args>
 *
 * Commands: buildRowDoc, buildColumnDoc, getRowOrder, getColumnOrder, applyDelta
 * YJS_PATH env var must point to the yjs package directory.
 */
"use strict";

const Y = require(process.env.YJS_PATH);

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
  const fg = new Y.Map();
  fg.set("field_id", fieldId);
  fg.set("ty", 3);
  const cg = new Y.Array();
  const children = groupIds.map((id) => {
    const m = new Y.Map();
    m.set("id", id);
    m.set("visible", true);
    return m;
  });
  if (children.length > 0) cg.insert(0, children);
  fg.set("groups", cg);
  groups.insert(0, [fg]);
  return Array.from(Y.encodeStateAsUpdate(doc));
}

function getRowOrder(docState, viewId) {
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

function getColumnOrder(docState, viewId, fieldId) {
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

function applyDelta(docState, delta) {
  const doc = new Y.Doc();
  Y.applyUpdate(doc, new Uint8Array(docState));
  Y.applyUpdate(doc, new Uint8Array(delta));
  return Array.from(Y.encodeStateAsUpdate(doc));
}

const cmd = process.argv[2];
const args = JSON.parse(process.argv[3]);
if (cmd === "buildRowDoc") process.stdout.write(JSON.stringify(buildRowDoc(...args)));
else if (cmd === "buildColumnDoc") process.stdout.write(JSON.stringify(buildColumnDoc(...args)));
else if (cmd === "getRowOrder") process.stdout.write(JSON.stringify(getRowOrder(...args)));
else if (cmd === "getColumnOrder") process.stdout.write(JSON.stringify(getColumnOrder(...args)));
else if (cmd === "applyDelta") process.stdout.write(JSON.stringify(applyDelta(...args)));
else {
  process.stderr.write("Unknown command: " + cmd + "\n");
  process.exit(1);
}
