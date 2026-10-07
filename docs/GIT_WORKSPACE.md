# Isolated Git workspace lease

Autonomous Loop42 code work should not run directly in the operator's normal checkout or on a branch that is treated as product truth. `git_workspace.py` creates a bounded detached Git worktree at one exact existing commit and returns a lease that can be revalidated before use or removal.

## Creation boundary

A lease:

- requires the exact Git top-level repository directory;
- accepts only a hexadecimal commit revision and resolves it to the exact full commit;
- requires an already-existing non-symlink parent outside the repository root;
- creates a generated `.loop42-worktree-*` path;
- uses `git worktree add --detach` with `shell=False`;
- verifies the resulting worktree HEAD equals the requested commit;
- performs no fetch, pull, branch checkout, commit, push, merge or network operation.

The generated worktree is therefore an isolated disposable coding workspace. Dirty edits in the lease do not change the operator's normal checkout.

## Validation and removal

`validate_worktree_lease(...)` rechecks the repository identity, workspace existence, detached HEAD commit and lease fingerprint. If the HEAD moved, validation fails closed.

`remove_worktree(...)` first validates the lease and then asks Git to remove only the generated leased worktree path. It refuses a path inside the repository root. A deliberately invalid or interrupted lease must be reconciled explicitly rather than "fixed" by guessing.

## Role in the autonomous loop

The intended runtime path is:

`exact source revision -> isolated worktree lease -> WorkerProvider -> ChangeSet -> policy/permit -> apply -> registered verification -> reconcile -> commit/PR/cleanup policy`

The model never receives authority to create or remove worktrees. The consumer/runtime owns that lifecycle.
