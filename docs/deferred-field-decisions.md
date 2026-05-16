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

Status: implemented for v1 single-file upload/download/delete and typed Media-cell
linking; multipart upload remains deferred.

What already works:

- Media cells with external/network URLs are supported in the typed row API.
- Docker proves that a media field can store and read back a network media entry.
- The returned AppFlowy shape normalizes `upload_type` to numeric `1`, which maps
  to `Network`.
- `upload_file_blob_v1` uploads local bytes to AppFlowy file storage.
- `get_file_blob_v1` downloads the stored bytes.
- `delete_file_blob_v1` deletes the stored blob.
- `upload_file_as_media` uploads a local file and returns a Media-cell object with
  `upload_type = Cloud`.
- Docker proves the flow with `parent_dir = database_id`: upload text file, download it,
  attach it to a Media field, read the row back with `upload_type = 2`, then clean up
  both row and blob.

What remains:

- Multipart upload for large files.
- Public size-limit policy and streaming behavior for larger blobs.
- Broader browser/UI visual proof for uploaded media previews.

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

Ship the v1 single-file workflow as the first upload slice. Keep it separate from the
generic typed row writer: callers upload the file first, receive a Media-cell object,
then pass that object to `create_typed_database_row` / `upsert_typed_database_row`.

Recommended next tasks:

1. Add multipart upload support for large files if users need it.
2. Add explicit public size limits and streaming behavior.
3. Add browser/UI preview evidence if AppFlowy Web reliably renders uploaded media.

Why it matters:

Network media is enough for many task-card use cases. Uploading real files is more
valuable, but it crosses into binary payload handling, storage cleanup, and possible
quota/security concerns. It should be implemented deliberately rather than hidden
inside a generic row writer.
