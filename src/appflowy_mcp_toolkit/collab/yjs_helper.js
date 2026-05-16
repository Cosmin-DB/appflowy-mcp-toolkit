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
  const now = Math.floor(Date.now() / 1000);
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

function mapFromObject(value) {
  const map = new Y.Map();
  for (const [key, item] of Object.entries(value || {})) {
    if (Array.isArray(item)) {
      const array = new Y.Array();
      array.insert(
        0,
        item.map((child) =>
          child instanceof Y.Map
            ? child
            : child && typeof child === "object"
              ? mapFromObject(child)
              : child
        )
      );
      map.set(key, array);
    } else {
      map.set(key, item);
    }
  }
  return map;
}

function childGroupId(group) {
  if (group instanceof Y.Map) return group.get("id");
  if (group && typeof group === "object") return group.id;
  return undefined;
}

function childGroupVisible(group) {
  if (group instanceof Y.Map) return group.get("visible");
  if (group && typeof group === "object") return group.visible;
  return undefined;
}

/**
 * Snapshot a single Y.Array/Y.Map/plain item to a plain-JS value before
 * a transaction so it can be safely deep-cloned back into the document.
 * Must be called BEFORE the item is deleted from its parent.
 */
function itemToJson(item) {
  if (item instanceof Y.Map) return item.toJSON();
  if (item instanceof Y.Array) return item.toArray().map(itemToJson);
  if (item && typeof item === "object") return JSON.parse(JSON.stringify(item));
  return item;
}

/**
 * Rebuild a fresh Yjs value (Y.Map / Y.Array / primitive) from a plain-JS
 * snapshot produced by itemToJson.  Primitives are returned as-is.
 */
function cloneFromJson(json) {
  if (json === null || json === undefined) return json;
  if (Array.isArray(json)) {
    const arr = new Y.Array();
    if (json.length > 0) arr.insert(0, json.map(cloneFromJson));
    return arr;
  }
  if (typeof json === "object") {
    const m = new Y.Map();
    for (const [k, v] of Object.entries(json)) m.set(k, cloneFromJson(v));
    return m;
  }
  return json;
}

function normalizeGroupArray(array) {
  for (let i = 0; i < array.length; i++) {
    const item = array.get(i);
    if (item instanceof Y.Map) {
      const children = item.get("groups");
      if (children instanceof Y.Array) normalizeGroupArray(children);
      continue;
    }
    if (item && typeof item === "object" && !Array.isArray(item)) {
      array.delete(i, 1);
      array.insert(i, [mapFromObject(item)]);
    }
  }
}

function addSelectOptionToDatabase(docStateBytes, input) {
  const doc = new Y.Doc();
  Y.applyUpdate(doc, docStateBytes);

  const svBefore = Y.encodeStateVector(doc);
  const root = doc.getMap("data");
  const database = root.get("database");
  if (!(database instanceof Y.Map)) {
    throw new Error("data.database not found or not a YMap in collab doc");
  }
  const fields = database.get("fields");
  if (!(fields instanceof Y.Map)) {
    throw new Error("data.database.fields not found or not a YMap in collab doc");
  }

  const field = fields.get(input.field_id);
  if (!(field instanceof Y.Map)) {
    throw new Error("Field not found in database collab: " + input.field_id);
  }
  const typeOption = field.get("type_option");
  if (!(typeOption instanceof Y.Map)) {
    throw new Error("Field type_option not found or not a YMap for field: " + input.field_id);
  }

  const selectOption = typeOption.get(String(input.field_type));
  if (!(selectOption instanceof Y.Map)) {
    throw new Error("Select field type option not found for field type: " + input.field_type);
  }

  const rawContent = selectOption.get("content");
  const content = rawContent ? JSON.parse(rawContent) : { options: [], disable_color: false };
  if (!Array.isArray(content.options)) content.options = [];

  const existing = content.options.find((option) => option.id === input.option_id || option.name === input.name);
  const option = existing || {
    id: input.option_id,
    name: input.name,
    color: input.color || "Purple",
  };

  const affectedViews = [];
  const now = Math.floor(Date.now() / 1000);

  doc.transact(() => {
    if (!existing) {
      content.options.push(option);
      selectOption.set("content", JSON.stringify(content));
    }
    field.set("last_modified", now);

    const views = database.get("views");
    if (views instanceof Y.Map) {
      for (const [viewId, viewData] of views.entries()) {
        if (!(viewData instanceof Y.Map)) continue;
        if (input.view_id && viewId !== input.view_id) continue;
        const groups = viewData.get("groups");
        if (!(groups instanceof Y.Array)) continue;
        normalizeGroupArray(groups);

        for (let i = 0; i < groups.length; i++) {
          const group = groups.get(i);
          if (!(group instanceof Y.Map) || group.get("field_id") !== input.field_id) continue;
          let childGroups = group.get("groups");
          if (!(childGroups instanceof Y.Array)) {
            childGroups = new Y.Array();
            group.set("groups", childGroups);
          }
          normalizeGroupArray(childGroups);
          if (!childGroups.toArray().some((child) => childGroupId(child) === input.option_id)) {
            childGroups.push([mapFromObject({ id: input.option_id, visible: true })]);
          }
          affectedViews.push(viewId);
        }
      }
    }
  });

  const deltaUpdate = Y.encodeStateAsUpdate(doc, svBefore);
  return {
    optionAdded: !existing,
    option,
    affectedViews: [...new Set(affectedViews)],
    deltaUpdate,
  };
}

function getSelectOptionContent(database, input) {
  const fields = database.get("fields");
  if (!(fields instanceof Y.Map)) {
    throw new Error("data.database.fields not found or not a YMap in collab doc");
  }

  const field = fields.get(input.field_id);
  if (!(field instanceof Y.Map)) {
    throw new Error("Field not found in database collab: " + input.field_id);
  }
  const typeOption = field.get("type_option");
  if (!(typeOption instanceof Y.Map)) {
    throw new Error("Field type_option not found or not a YMap for field: " + input.field_id);
  }

  const selectOption = typeOption.get(String(input.field_type));
  if (!(selectOption instanceof Y.Map)) {
    throw new Error("Select field type option not found for field type: " + input.field_type);
  }

  const rawContent = selectOption.get("content");
  const content = rawContent ? JSON.parse(rawContent) : { options: [], disable_color: false };
  if (!Array.isArray(content.options)) content.options = [];
  return { field, selectOption, content };
}

function findOption(options, input) {
  const optionId = input.option_id;
  const optionName = input.option_name || input.name;
  return options.find(
    (option) =>
      (optionId !== undefined && option.id === optionId) ||
      (optionName !== undefined && option.name === optionName)
  );
}

function renameSelectOptionInDatabase(docStateBytes, input) {
  const doc = new Y.Doc();
  Y.applyUpdate(doc, docStateBytes);

  const svBefore = Y.encodeStateVector(doc);
  const root = doc.getMap("data");
  const database = root.get("database");
  if (!(database instanceof Y.Map)) {
    throw new Error("data.database not found or not a YMap in collab doc");
  }

  const { field, selectOption, content } = getSelectOptionContent(database, input);
  const option = findOption(content.options, input);
  if (!option) {
    throw new Error("Select option not found");
  }
  const duplicate = content.options.find(
    (candidate) => candidate.id !== option.id && candidate.name === input.new_name
  );
  if (duplicate) {
    throw new Error("Select option name already exists: " + input.new_name);
  }

  const beforeName = option.name;
  const now = Math.floor(Date.now() / 1000);
  doc.transact(() => {
    option.name = input.new_name;
    selectOption.set("content", JSON.stringify(content));
    field.set("last_modified", now);
  });

  const deltaUpdate = Y.encodeStateAsUpdate(doc, svBefore);
  return {
    optionId: option.id,
    previousName: beforeName,
    option,
    renamed: beforeName !== input.new_name,
    deltaUpdate,
  };
}

function setSelectOptionVisibilityInDatabase(docStateBytes, input) {
  const doc = new Y.Doc();
  Y.applyUpdate(doc, docStateBytes);

  const svBefore = Y.encodeStateVector(doc);
  const root = doc.getMap("data");
  const database = root.get("database");
  if (!(database instanceof Y.Map)) {
    throw new Error("data.database not found or not a YMap in collab doc");
  }

  const { content } = getSelectOptionContent(database, input);
  const option = findOption(content.options, input);
  if (!option) {
    throw new Error("Select option not found");
  }

  const affectedViews = [];
  const visibilityByView = {};
  const views = database.get("views");
  doc.transact(() => {
    if (!(views instanceof Y.Map)) return;
    for (const [viewId, viewData] of views.entries()) {
      if (!(viewData instanceof Y.Map)) continue;
      if (input.view_id && viewId !== input.view_id) continue;
      const groups = viewData.get("groups");
      if (!(groups instanceof Y.Array)) continue;
      normalizeGroupArray(groups);

      for (let i = 0; i < groups.length; i++) {
        const group = groups.get(i);
        if (!(group instanceof Y.Map) || group.get("field_id") !== input.field_id) continue;
        const childGroups = group.get("groups");
        if (!(childGroups instanceof Y.Array)) continue;
        normalizeGroupArray(childGroups);

        for (let j = 0; j < childGroups.length; j++) {
          const child = childGroups.get(j);
          if (childGroupId(child) !== option.id) continue;
          const before = childGroupVisible(child);
          if (child instanceof Y.Map) {
            child.set("visible", input.visible);
          } else {
            childGroups.delete(j, 1);
            childGroups.insert(j, [mapFromObject({ ...child, visible: input.visible })]);
          }
          affectedViews.push(viewId);
          visibilityByView[viewId] = { before, after: input.visible };
        }
      }
    }
  });

  const deltaUpdate = Y.encodeStateAsUpdate(doc, svBefore);
  return {
    option,
    visible: input.visible,
    affectedViews: [...new Set(affectedViews)],
    visibilityByView,
    deltaUpdate,
  };
}

/**
 * Reorder a row inside a specific database view's row_orders.
 *
 * Input:
 *   operation: "reorder_row"
 *   doc_state: [...]
 *   view_id: "<uuid>"          // required: target view
 *   row_id:  "<uuid>"          // row to move
 *   before_row_id: "<uuid>" | null  // insert before this row; null = append to end
 */
function reorderRowInView(docStateBytes, input) {
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

  const viewData = views.get(input.view_id);
  if (!(viewData instanceof Y.Map)) {
    throw new Error("View not found in collab doc: " + input.view_id);
  }
  const ro = viewData.get("row_orders");
  if (!(ro instanceof Y.Array)) {
    throw new Error("row_orders not found or not a YArray for view: " + input.view_id);
  }

  const items = ro.toArray();
  const fromIndex = items.findIndex((item) => getRowId(item) === input.row_id);
  if (fromIndex === -1) {
    throw new Error("row_id not found in row_orders for view: " + input.row_id);
  }

  let toIndex;
  if (input.before_row_id === null || input.before_row_id === undefined) {
    // append to end
    toIndex = items.length - 1;
  } else {
    toIndex = items.findIndex((item) => getRowId(item) === input.before_row_id);
    if (toIndex === -1) {
      throw new Error("before_row_id not found in row_orders: " + input.before_row_id);
    }
    // If moving forward, the target shifts by one after removal
    if (fromIndex < toIndex) toIndex -= 1;
  }

  if (fromIndex === toIndex) {
    // No-op
    const deltaUpdate = Y.encodeStateAsUpdate(doc, svBefore);
    return { moved: false, from_index: fromIndex, to_index: toIndex, deltaUpdate };
  }

  // Snapshot BEFORE the transaction so the YMap is still readable.
  const movingSnapshot = itemToJson(items[fromIndex]);
  doc.transact(() => {
    ro.delete(fromIndex, 1);
    const insertAt = Math.min(toIndex, ro.length);
    ro.insert(insertAt, [cloneFromJson(movingSnapshot)]);
  });

  const deltaUpdate = Y.encodeStateAsUpdate(doc, svBefore);
  return { moved: true, from_index: fromIndex, to_index: toIndex, deltaUpdate };
}

/**
 * Reorder a board column (child group under the grouped field's group entry)
 * inside a specific database view.
 *
 * This reorders entries in the view's groups[field_id].groups (child groups),
 * which controls board column order for Status-grouped boards.
 *
 * Input:
 *   operation:      "reorder_column"
 *   doc_state:      [...]
 *   view_id:        "<uuid>"           // required: target view
 *   field_id:       "<uuid>"           // grouping field id (e.g. Status field)
 *   group_id:       "<uuid>"           // child group (column) to move
 *   before_group_id: "<uuid>" | null   // insert before this group; null = append
 */
function reorderColumnInView(docStateBytes, input) {
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

  const viewData = views.get(input.view_id);
  if (!(viewData instanceof Y.Map)) {
    throw new Error("View not found in collab doc: " + input.view_id);
  }

  const groups = viewData.get("groups");
  if (!(groups instanceof Y.Array)) {
    throw new Error("groups not found or not a YArray for view: " + input.view_id);
  }
  normalizeGroupArray(groups);

  // Find the top-level group entry for this field
  let fieldGroupEntry = null;
  for (let i = 0; i < groups.length; i++) {
    const g = groups.get(i);
    if (g instanceof Y.Map && g.get("field_id") === input.field_id) {
      fieldGroupEntry = g;
      break;
    }
  }
  if (!fieldGroupEntry) {
    throw new Error("No group entry found for field_id: " + input.field_id + " in view: " + input.view_id);
  }

  const childGroups = fieldGroupEntry.get("groups");
  if (!(childGroups instanceof Y.Array)) {
    throw new Error("groups[field_id].groups not a YArray for field: " + input.field_id);
  }
  normalizeGroupArray(childGroups);

  const childItems = childGroups.toArray();
  const fromIndex = childItems.findIndex((item) => childGroupId(item) === input.group_id);
  if (fromIndex === -1) {
    throw new Error("group_id not found in child groups: " + input.group_id);
  }

  let toIndex;
  if (input.before_group_id === null || input.before_group_id === undefined) {
    toIndex = childItems.length - 1;
  } else {
    toIndex = childItems.findIndex((item) => childGroupId(item) === input.before_group_id);
    if (toIndex === -1) {
      throw new Error("before_group_id not found in child groups: " + input.before_group_id);
    }
    if (fromIndex < toIndex) toIndex -= 1;
  }

  if (fromIndex === toIndex) {
    const deltaUpdate = Y.encodeStateAsUpdate(doc, svBefore);
    return { moved: false, from_index: fromIndex, to_index: toIndex, deltaUpdate };
  }

  // Snapshot BEFORE the transaction so the YMap is still readable.
  const movingSnapshot = itemToJson(childItems[fromIndex]);
  doc.transact(() => {
    childGroups.delete(fromIndex, 1);
    const insertAt = Math.min(toIndex, childGroups.length);
    childGroups.insert(insertAt, [cloneFromJson(movingSnapshot)]);
  });

  const deltaUpdate = Y.encodeStateAsUpdate(doc, svBefore);
  return { moved: true, from_index: fromIndex, to_index: toIndex, deltaUpdate };
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
      } else if (operation === "add_select_option") {
        for (const key of ["field_id", "field_type", "option_id", "name"]) {
          if (input[key] === undefined || input[key] === null || input[key] === "") {
            throw new Error("add_select_option input must include " + key);
          }
        }
        result = addSelectOptionToDatabase(new Uint8Array(doc_state), input);
      } else if (operation === "rename_select_option") {
        for (const key of ["field_id", "field_type", "new_name"]) {
          if (input[key] === undefined || input[key] === null || input[key] === "") {
            throw new Error("rename_select_option input must include " + key);
          }
        }
        if (!input.option_id && !input.option_name) {
          throw new Error("rename_select_option input must include option_id or option_name");
        }
        result = renameSelectOptionInDatabase(new Uint8Array(doc_state), input);
      } else if (operation === "set_select_option_visibility") {
        for (const key of ["field_id", "field_type", "visible"]) {
          if (input[key] === undefined || input[key] === null || input[key] === "") {
            throw new Error("set_select_option_visibility input must include " + key);
          }
        }
        if (!input.option_id && !input.option_name) {
          throw new Error("set_select_option_visibility input must include option_id or option_name");
        }
        if (typeof input.visible !== "boolean") {
          throw new Error("set_select_option_visibility input visible must be boolean");
        }
        result = setSelectOptionVisibilityInDatabase(new Uint8Array(doc_state), input);
      } else if (operation === "reorder_row") {
        for (const key of ["view_id", "row_id"]) {
          if (input[key] === undefined || input[key] === null || input[key] === "") {
            throw new Error("reorder_row input must include " + key);
          }
        }
        result = reorderRowInView(new Uint8Array(doc_state), input);
      } else if (operation === "reorder_column") {
        for (const key of ["view_id", "field_id", "group_id"]) {
          if (input[key] === undefined || input[key] === null || input[key] === "") {
            throw new Error("reorder_column input must include " + key);
          }
        }
        result = reorderColumnInView(new Uint8Array(doc_state), input);
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
      if (operation === "add_select_option") {
        process.stdout.write(
          JSON.stringify({
            ok: true,
            option_added: result.optionAdded,
            option: result.option,
            affected_views: result.affectedViews,
            delta_update: Array.from(result.deltaUpdate),
          })
        );
      } else if (operation === "rename_select_option") {
        process.stdout.write(
          JSON.stringify({
            ok: true,
            option_id: result.optionId,
            previous_name: result.previousName,
            option: result.option,
            renamed: result.renamed,
            delta_update: Array.from(result.deltaUpdate),
          })
        );
      } else if (operation === "set_select_option_visibility") {
        process.stdout.write(
          JSON.stringify({
            ok: true,
            option: result.option,
            visible: result.visible,
            affected_views: result.affectedViews,
            visibility_by_view: result.visibilityByView,
            delta_update: Array.from(result.deltaUpdate),
          })
        );
      } else if (operation === "reorder_row" || operation === "reorder_column") {
        process.stdout.write(
          JSON.stringify({
            ok: true,
            moved: result.moved,
            from_index: result.from_index,
            to_index: result.to_index,
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
    }
  });
}

main();
