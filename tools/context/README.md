# Context tools

Reusable context assembly, source identity, stale-state and guarded checkpoint helpers.

## Implemented

`project_context.py` now provides a project-agnostic extraction of the context mechanics first proven in CORA:

- explicit consumer manifest (`loop42.context-manifest.v1`)
- exact local Git HEAD + manifest/source hashes
- deduplicated source inclusion
- no silent truncation
- stale-basis rejection
- single-writer lock across linked worktrees
- atomic checkpoint writeback to the consumer-owned `project_state`
- no commit/push authority

Consumer-specific manifests and product state remain in the consumer repository. Loop42 reads and guards them; it does not own them.

The default manifest name is `loop42-context.json`. A consumer may choose another path explicitly with `--manifest`.
