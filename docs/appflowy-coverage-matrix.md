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
| Workspaces read/basic create | medium-high | high for read/create, low for admin |
| Folder/view/page read | high | high for tree/page read, medium for mutations |
| Database schema/rows/tasks | high | high for task lifecycle data plane |
| Database fields | low-medium | read done, create candidate |
| Collab diagnostics/delete | medium | high for diagnostics/delete, low for arbitrary mutations |
| Files/blobs | read metadata/usage | high for metadata, writes deferred |
| Trash/favorites/recent | read implemented | high |
| Sharing/publishing | none | candidate but safety-sensitive |
| Search | read implemented | medium; depends on search service |
| Quick notes | CRUD implemented, dry-run writes | medium until self-hosted smoke expands |
| Chat/AI | none | deferred |
| Members/invites/admin | very low | safety-sensitive/deferred by default |

## Object And Operation Matrix

| Object family | Read/list | Create | Update/move | Delete/trash | Current status | Next decision |
|---|---|---|---|---|---|---|
| Workspace | list/settings/members/usage implemented | create implemented, dry-run default | patch/open routes exist | delete/leave/member removal routes exist | partial | Keep destructive admin gated or deferred |
| Space | folder tree shows spaces | source route exists: POST /space | source route exists: PATCH /space/{view_id} | via page/view trash/delete semantics | candidate | Implement only after page/view contract is tested |
| Folder/view/page tree | get folder/page-view implemented | page-view create/duplicate/database-view implemented dry-run default | update/rename/favorite/reorder/move implemented dry-run default | trash/restore/delete-trashed and bulk trash ops implemented dry-run default | broad page/view surface implemented | Add self-hosted page lifecycle smoke next |
| Document/page body | row document text supported on row create/detail | append-block implemented dry-run default | collab/document updates are deeper | trash via page-view routes | partial | Defer full block editor |
| Database list | list databases implemented | database-view route exists | view/layout routes likely collab-backed | page-view trash/delete | partial | Add database-view creation only after page/view work |
| Database fields | list fields implemented | POST /database/{database_id}/fields route exists | no safe update/delete route confirmed from matrix yet | no safe delete route confirmed | partial | Implement create field only after payload schema is mapped and tested |
| Database rows | list ids/details implemented | create/upsert implemented | upsert/update, status move implemented | no REST delete; Yjs row-order delete implemented | high | Add updated-row listing and broader field type tests |
| Task board | list/create/update/move/delete implemented | implemented | implemented | implemented via Yjs row-order delete | high for data plane | Add browser UI acceptance for Grid/Board |
| Row/card ordering | row_orders read implemented | n/a | reorder requires Yjs mutation | n/a | diagnostic only | Defer until browser behavior is mapped |
| Collab documents | JSON/raw/blob diff read implemented | create collab route exists | web-update used only for row delete | delete collab route exists but dangerous | partial | Keep generic collab writes private/diagnostic; do not expose broad destructive collab delete |
| File storage/blobs | usage/list/metadata implemented | upload routes exist | multipart complete routes exist | delete blob routes exist | read metadata implemented | Upload/delete deferred behind explicit gates |
| Trash | trash list implemented | n/a | single restore implemented dry-run default | single delete-from-trash implemented dry-run default | partial | Bulk restore/delete deferred |
| Favorites/recent | recent/favorite list implemented | add recent implemented dry-run default | favorite toggle/reorder implemented dry-run default | n/a | mostly implemented | Browser polish deferred |
| Sharing/guests | list shared views exists | share view route exists | revoke/access detail routes exist | revoke route exists | missing | Safety-sensitive; require explicit gates |
| Publishing | many publish-info/publish routes exist | publish routes exist | patch/unpublish/default namespace routes exist | delete published collabs route exists | missing | Safety-sensitive; document first, implement later |
| Search | search implemented | n/a | n/a | n/a | read implemented | AI summary endpoint deferred |
| Quick notes | list implemented | create implemented dry-run default | update implemented dry-run default | delete implemented dry-run default | CRUD implemented | Add self-hosted smoke if quick notes are enabled in local stack |
| Chat/AI | many chat/AI routes exist | create chat/question/answer/context | settings/question update | delete chat | missing | Defer: product-specific, may depend on AI services |
| Import | create/import/detail routes exist | import route exists | n/a | n/a | missing | Defer until release; external side effects |
| Access requests/invites/members | routes exist | invite/join/approve routes exist | member update exists | member/workspace delete exists | missing | Admin/security-sensitive; read-only first |

## Implementation Order

1. **Close task-board confidence**
   - Browser/UI acceptance against local AppFlowy Web.
   - Keep Board/Grid refresh bug documented separately from data-plane truth.

2. **Broaden low-risk read coverage**
   - Updated row ids. **Done.**
   - Workspace settings/members/usage read. **Done.**
   - Recent/favorite/trash list. **Done.**
   - Search. **Done, AI summary deferred.**

3. **Page/view management**
   - Create page view. **Done, dry-run default.**
   - Read/update page name/icon/extra. **Done, dry-run default for writes.**
   - Move page. **Done, dry-run default.**
   - Move to trash / restore from trash / delete from trash with gates. **Single-page and bulk routes done, dry-run default.**

4. **Database/field expansion**
   - Database view creation if payload is stable.
   - Field creation for simple field types.
   - More field-type write tests for rows.

5. **Files**
   - Usage/list metadata/get metadata. **Done.**
   - Blob download/upload/delete deferred until binary/file delivery semantics are designed.

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

Add live/self-hosted smoke coverage for the newly exposed page-view and quick-note
surfaces. The code surface is broad now; the next quality gain is proving those
routes against disposable AppFlowy state instead of adding risky publishing/admin
operations.
