# AppFlowy Coverage Matrix

This file tracks the project goal: the MCP should eventually do as much of AppFlowy as
is safe and realistically supported.

The matrix is intentionally split into three states:

- **Implemented**: exposed through client/CLI/MCP and covered by tests or live smoke.
- **Candidate**: endpoint/source route exists, but the MCP does not expose it yet.
- **Deferred**: risky, admin-heavy, AI/product-specific, undocumented, or needs deeper browser/collab research.

## Current Summary

The toolkit is strong for database-backed task boards, page/view organization, and local
self-hosted AppFlowy smoke testing. It is not a full AppFlowy administration MCP.

Approximate coverage by object family:

| Area | Current coverage | Confidence |
|---|---:|---|
| Server/user read | basic read | high |
| Workspaces read/basic create | medium-high | high for read/create, low for admin |
| Folder/view/page read | high | high for tree/page read, medium for mutations |
| Database schema/rows/tasks | high | high for task lifecycle data plane |
| Database fields | medium | read/create done, field-type payloads are caller supplied |
| Database typed fields | high | most task-card/scalar fields and Media uploads covered; relation/translate deferred |
| Collab diagnostics/update/delete | medium | high for diagnostics/delete and row-id cell updates, low for arbitrary mutations |
| Files/blobs | metadata plus v1 upload/download/delete | high for Docker-proven single-file flow |
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
| Space | folder tree shows spaces | create space implemented dry-run default | update space implemented dry-run default | via page/view trash/delete semantics | implemented except dedicated delete | Add self-hosted org-structure smoke next |
| Folder/view/page tree | get folder/page-view implemented | folder-view/page-view create, duplicate, database-view implemented dry-run default | update/rename/favorite/reorder/move implemented dry-run default | trash/restore/delete-trashed and bulk trash ops implemented dry-run default | broad page/view surface implemented and self-hosted page lifecycle smoke added | Full browser UI automation remains separate |
| Document/page body | row document text supported on row create/detail | append-block implemented dry-run default | collab/document updates are deeper | trash via page-view routes | partial | Defer full block editor |
| Database list | list databases implemented | database-view route exists | view/layout routes likely collab-backed | page-view trash/delete | partial | Add database-view creation only after page/view work |
| Database fields | list fields implemented | create field implemented dry-run default | no safe update/delete route confirmed from matrix yet | no safe delete route confirmed | partial | Add friendly field-type builders later; raw payload route exists now |
| Database rows | list ids/details implemented | create/upsert implemented | upsert/update, status move, and row-id collab update implemented | no REST delete; Yjs row-order delete implemented | high | Broaden field type tests and keep collab mutations narrowly scoped |
| Typed row cells | schema parsing implemented | typed create/upsert implemented | typed upsert implemented | delete via row delete path | common + scalar + network media fields Docker-proven | Investigate relation/translate and media upload workflows |
| Task board | list plus Description exact/contains search implemented | Status option/board column add implemented | managed task move, manual row-id move, Description-resolved update/move with ambiguity guard, Status option rename/hide/show, row/card reorder, and board column reorder implemented | row/card delete via Yjs row-order delete, including Description-resolved delete with ambiguity guard; Status option delete deferred | high for data plane, medium for structural view mutations | Add browser UI acceptance for Grid/Board and ordering |
| Row/card ordering | row_orders read implemented | n/a | row/card reorder implemented via narrow Yjs row_orders mutation; board column reorder implemented via groups[field_id].groups mutation | n/a | unit + offline Yjs helper integration covered; Docker/browser proof pending | Add local Docker/browser ordering acceptance |
| Database view configuration | filters/sorts/groups/field settings/layout settings read implemented | n/a | updates require Yjs view mutation proof | n/a | diagnostic only | Keep read-only until Docker/self-hosted proof exists |
| Collab documents | JSON/raw/blob diff read implemented | create collab route exists | web-update used for row delete and DatabaseRow cell updates only | delete collab route exists but dangerous | partial | Keep generic collab writes private/diagnostic; do not expose broad destructive collab delete |
| File storage/blobs | usage/list/metadata and v1 blob download implemented | v1 single-upload implemented; multipart routes mapped but deferred | multipart complete routes mapped but deferred | v1 blob delete implemented | v1 upload/download/delete Docker-proven; Media-cell linking Docker-proven | Add multipart only if large-file demand appears |
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
   - Database view configuration diagnostics. **Done, read-only.**

3. **Page/view management**
   - Create/update space. **Done, dry-run default, self-hosted smoke covered.**
   - Create folder view. **Implemented, dry-run default; current self-hosted 0.15.17 image returns 404 for this route despite the pinned source route existing.**
   - Create page view. **Done, dry-run default, self-hosted smoke covered.**
   - Read/update page name/icon/extra. **Done, dry-run default for writes.**
   - Move page. **Done, dry-run default, self-hosted smoke covered.**
   - Move to trash / restore from trash / delete from trash with gates. **Single-page and bulk routes done, dry-run default; single-page path covered by self-hosted smoke.**

4. **Database/field expansion**
   - Database view creation if payload is stable.
   - Field creation for simple field types.
   - More field-type write tests for rows.

5. **Files**
   - Usage/list metadata/get metadata. **Done.**
   - V1 single-file upload/download/delete. **Done, Docker-proven.**
   - Uploaded file to typed Media-cell linking. **Done, Docker-proven.**
   - Multipart upload. **Deferred until large-file demand appears.**

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
- Human-name task mutations must resolve to exactly one Description match; duplicates return candidates and do not write.
- The MCP should expose bounded tools, not replace the calling AI's reasoning.
  Avoid fuzzy intent resolution and broad internal-JSON mutation endpoints.

## Immediate Next Implementable Slice

The main implementation surface is now broad enough for a publishable pre-1.0 toolkit.
Remaining finish work should focus on release evidence, not new risky feature families:

- see `TODO.md` for the current task-board-first backlog and deferred page/document work
- full gate battery from a clean checkout
- package/build verification
- secret/private-id scan
- browser UI acceptance with Playwright or an allowed browser profile
- docs pass that clearly marks deferred publishing/sharing/admin/import/AI surfaces
