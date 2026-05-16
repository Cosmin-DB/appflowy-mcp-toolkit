# AppFlowy Coverage Matrix

This file tracks the goal Cosmin set: the MCP should eventually do as much of AppFlowy as is safe and realistically supported.

The matrix is intentionally split into three states:

- **Implemented**: exposed through client/CLI/MCP and covered by tests or live smoke.
- **Candidate**: endpoint/source route exists, but the MCP does not expose it yet.
- **Deferred**: risky, admin-heavy, AI/product-specific, undocumented, or needs deeper browser/collab research.

## Current Summary

The toolkit is strong for database-backed task boards, and now has a local self-hosted AppFlowy test rig. It is not yet a full AppFlowy administration MCP.

Approximate coverage by object family:

| Area | Current coverage | Confidence |
|---|---:|---|
| Workspaces read/basic create | medium | high for read/create, low for admin |
| Folder/view/page read | medium | high for tree/read, medium for mutations |
| Database schema/rows/tasks | high | high for task lifecycle data plane |
| Database fields | low-medium | read done, create candidate |
| Collab diagnostics/delete | medium | high for diagnostics/delete, low for arbitrary mutations |
| Files/blobs | none | candidate |
| Trash/favorites/recent | low | candidate |
| Sharing/publishing | none | candidate but safety-sensitive |
| Search | none | candidate read-only |
| Quick notes | none | candidate |
| Chat/AI | none | deferred |
| Members/invites/admin | very low | safety-sensitive/deferred by default |

## Object And Operation Matrix

| Object family | Read/list | Create | Update/move | Delete/trash | Current status | Next decision |
|---|---|---|---|---|---|---|
| Workspace | list implemented | create implemented, dry-run default | patch/open/settings/member routes exist | delete/leave/member removal routes exist | partial | Add read settings/members first; keep destructive admin gated or deferred |
| Space | folder tree shows spaces | source route exists: POST /space | source route exists: PATCH /space/{view_id} | via page/view trash/delete semantics | candidate | Implement only after page/view contract is tested |
| Folder/view/page tree | get folder implemented | folder-view/page-view routes exist | update name/icon/extra/favorite/move routes exist | move-to-trash/restore/delete-trash routes exist | read implemented, mutations missing | Next major block after tasks |
| Document/page body | row document text supported on row create/detail | append-block route exists | collab/document updates are deeper | trash via page-view routes | partial | Start with page metadata and append-block only; defer full block editor |
| Database list | list databases implemented | database-view route exists | view/layout routes likely collab-backed | page-view trash/delete | partial | Add database-view creation only after page/view work |
| Database fields | list fields implemented | POST /database/{database_id}/fields route exists | no safe update/delete route confirmed from matrix yet | no safe delete route confirmed | partial | Implement create field only after payload schema is mapped and tested |
| Database rows | list ids/details implemented | create/upsert implemented | upsert/update, status move implemented | no REST delete; Yjs row-order delete implemented | high | Add updated-row listing and broader field type tests |
| Task board | list/create/update/move/delete implemented | implemented | implemented | implemented via Yjs row-order delete | high for data plane | Add browser UI acceptance for Grid/Board |
| Row/card ordering | row_orders read implemented | n/a | reorder requires Yjs mutation | n/a | diagnostic only | Defer until browser behavior is mapped |
| Collab documents | JSON/raw/blob diff read implemented | create collab route exists | web-update used only for row delete | delete collab route exists but dangerous | partial | Keep generic collab writes private/diagnostic; do not expose broad destructive collab delete |
| File storage/blobs | routes exist for metadata, list, usage, get blob | upload routes exist | multipart complete routes exist | delete blob routes exist | missing | Good later block: read metadata/usage first, upload/delete gated |
| Trash | trash list route exists | n/a | restore page/all routes exist | delete page/all from trash routes exist | missing | Add read trash and single restore first; bulk delete last |
| Favorites/recent | recent/favorite list routes exist | add recent route exists | reorder favorite route exists | favorite toggle route exists | missing | Low-risk convenience block |
| Sharing/guests | list shared views exists | share view route exists | revoke/access detail routes exist | revoke route exists | missing | Safety-sensitive; require explicit gates |
| Publishing | many publish-info/publish routes exist | publish routes exist | patch/unpublish/default namespace routes exist | delete published collabs route exists | missing | Safety-sensitive; document first, implement later |
| Search | search and summary endpoints exist | n/a | n/a | n/a | missing | Good read-only block if local search service works |
| Quick notes | list route exists | create route exists | update route exists | delete route exists | missing | Small candidate block |
| Chat/AI | many chat/AI routes exist | create chat/question/answer/context | settings/question update | delete chat | missing | Defer: product-specific, may depend on AI services |
| Import | create/import/detail routes exist | import route exists | n/a | n/a | missing | Defer until release; external side effects |
| Access requests/invites/members | routes exist | invite/join/approve routes exist | member update exists | member/workspace delete exists | missing | Admin/security-sensitive; read-only first |

## Implementation Order

1. **Close task-board confidence**
   - Browser/UI acceptance against local AppFlowy Web.
   - Keep Board/Grid refresh bug documented separately from data-plane truth.

2. **Broaden low-risk read coverage**
   - Updated row ids.
   - Workspace settings/members read.
   - Recent/favorite/trash list.
   - Search if service works in Docker.

3. **Page/view management**
   - Create page view.
   - Read/update page name/icon/extra.
   - Move page.
   - Move to trash / restore from trash / delete from trash with gates.

4. **Database/field expansion**
   - Database view creation if payload is stable.
   - Field creation for simple field types.
   - More field-type write tests for rows.

5. **Files**
   - Usage/list metadata/get blob.
   - Upload/delete only behind explicit gates.

6. **Sharing/publishing/admin**
   - Document and test carefully.
   - Mutations require explicit opt-in gates and likely separate release phase.

## Safety Rules For Broad Coverage

- Read-only operations can be added freely when routes are stable.
- Mutations must be dry-run by default.
- Destructive operations need explicit env gates and tests against local Docker.
- Anything involving sharing, publishing, members, invites, deletion, or imports must not be enabled casually.
- Browser UI acceptance is required for user-visible page/view/task flows.
- Data-plane verification remains separate from AppFlowy Web rendering.

## Immediate Next Implementable Slice

Add the documented low-risk row sync endpoint:

`GET /api/workspace/{workspace_id}/database/{database_id}/row/updated?after=<date-time>`

This improves incremental sync without adding new destructive behavior.

