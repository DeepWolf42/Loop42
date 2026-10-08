# One autonomous attempt

Loop42 can now compose its bounded pieces into one complete coding attempt without granting the model direct execution authority.

## Sequence

```
exact Git revision
    ↓
isolated detached worktree
    ↓
WorkerProvider.run()
    ↓
exact result-identity check
    ↓
ChangeSet v1 normalization
    ↓
action policy + short-lived permit
    ↓
workspace apply
    ↓
registered verification IDs
    ↓
structured attempt result
```

The request's source revision is resolved to the exact full commit before the provider is called. The provider result must repeat the exact task ID, attempt ID, full source revision and context fingerprint or the attempt fails closed.

A provider BLOCKED/FAILED result causes no code change. A proposal is snapshotted from the isolated worktree, normalized and policy-gated before apply.

A changed workspace is only `VERIFIED` when at least one requested, pre-registered verification ran and all returned success. If no verification is requested the result is explicitly `APPLIED_UNVERIFIED`. Failed verification leaves the candidate change inside the isolated worktree for later retry/recovery analysis; it never changes the operator's normal checkout.

## Deliberately not included

This runner performs exactly one visible attempt. It does not:

- retry or silently fall back to another provider;
- commit or push;
- open or merge a pull request;
- publish/release;
- delete the isolated worktree automatically;
- treat a passing test as merge authority.

The caller owns later cleanup and the next state-machine decision. This keeps future retry, provider routing, recovery and Git publication observable to Loop42 rather than hidden inside a worker adapter.
