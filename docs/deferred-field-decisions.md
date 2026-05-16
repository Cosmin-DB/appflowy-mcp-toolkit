# Deferred Field Decisions

This note records the rich database field work that is intentionally not exposed yet.
It is meant to leave a clear trail for future contributors instead of hiding hard
edges behind vague "not supported" wording.

## Relation

Status: deferred.

What we know:

- AppFlowy Collab represents relation cells as a row-id list, with the observed shape
  `{ "row_ids": [...] }`.
- A Docker experiment accepted a relation-shaped cell write.
- The same row read back through the REST row-detail route did not include the relation
  value.
- Upstream AppFlowy Cloud tests also treat relation-style field writes as unsupported
  through the normal database row route.

Decision:

Do not expose relation writes through the public typed row API yet. A relation tool
needs a separate investigation of linked database setup, relation field configuration,
and the exact read path that AppFlowy Web uses after the write.

Why it matters:

Relation is useful for linking tasks to other records, but a write that disappears from
the normal row read path would give agents false confidence. The MCP should reject it
clearly until we can prove create, update, read-back, and cleanup against Docker.

## Translate

Status: deferred.

What we know:

- The typed writer can form a manual string-like payload for the Translate field.
- Docker accepts the write route, but row-detail reads return an empty value.
- Translate is likely tied to AppFlowy's product/AI flow rather than being a normal
  user-authored database cell.

Decision:

Keep Translate out of the typed writer until the product flow is mapped. If it is added,
it should probably be an AI/translation workflow tool, not just another row-cell builder.

Why it matters:

Agents should not be invited to write values that AppFlowy ignores or recomputes. The
current behavior looks product-managed, so a low-level write API would be misleading.

## Media Uploads

Status: partially supported; upload workflow deferred.

What already works:

- Media cells with external/network URLs are supported in the typed row API.
- Docker proves that a media field can store and read back a network media entry.
- The returned AppFlowy shape normalizes `upload_type` to numeric `1`, which maps
  to `Network`.

What remains:

- Uploading bytes into AppFlowy file storage.
- Reading raw blob bytes back.
- Deleting uploaded blobs.
- Linking the uploaded blob URL into a Media cell with `upload_type = Cloud`.
- Proving the parent directory convention for database-card attachments.

Evidence from upstream source:

- `PUT /api/file_storage/{workspace_id}/v1/blob/{parent_dir}` accepts raw bytes,
  requires `Content-Type` and `Content-Length`, generates a content-derived
  `file_id`, and stores the object under `workspace_id/parent_dir/file_id`.
- `GET /api/file_storage/{workspace_id}/v1/blob/{parent_dir}/{file_id}` fetches the
  blob bytes.
- `GET /api/file_storage/{workspace_id}/v1/metadata/{parent_dir}/{file_id}` fetches
  metadata.
- `DELETE /api/file_storage/{workspace_id}/v1/blob/{parent_dir}/{file_id}` deletes
  the blob.
- Multipart routes also exist: `create_upload`, `upload_part`, and
  `complete_upload`.
- AppFlowy source defines media upload types as `Local = 0`, `Network = 1`,
  `Cloud = 2`; file types include Image, Link, Document, Archive, Video, Audio, and
  Text.
- Upstream tests use parent directories such as the workspace id, `file/v1/image`,
  and chat ids. That proves the storage API, but not yet the best parent directory for
  database-card media attachments.

Decision:

Treat media upload as the next interesting slice, but keep it outside the current
typed-cell release. The right implementation is a dedicated file-storage layer first,
then a small helper that uploads a local file and returns a Media-cell object that can
be written by `create_typed_database_row` / `upsert_typed_database_row`.

Recommended next tasks:

1. Add a private client proof for v1 single-file upload against Docker.
2. Verify download, metadata, and delete for the returned `file_id`.
3. Decide and prove the `parent_dir` convention for database media attachments.
4. Write a Docker smoke that uploads a tiny disposable file, links it into a Media
   field as `Cloud`, reads the row back, then deletes both row and blob.
5. Only then expose public MCP tools, behind write gates and with size limits.

Why it matters:

Network media is enough for many task-card use cases. Uploading real files is more
valuable, but it crosses into binary payload handling, storage cleanup, and possible
quota/security concerns. It should be implemented deliberately rather than hidden
inside a generic row writer.

