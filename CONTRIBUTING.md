# Contributing

This project is early. Please keep contributions small, tested, and generic.

Before submitting changes:

- run tests/lint/typecheck when available;
- do not add secrets or private account data;
- avoid copying code from unlicensed or license-incompatible repositories;
- keep new write/admin surface behind explicit safety design, dry-run defaults, and
  disposable live/self-hosted tests. Existing guarded task/page/quick-note writes are
  intentional; publishing, sharing, invites, admin/member mutations, imports, AI/chat,
  and broad file upload/delete remain out of scope for the first release candidate.
