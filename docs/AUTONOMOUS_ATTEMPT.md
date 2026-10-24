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

A provider BLOCKED/FAILED result causes no code change. The attempt runner itself (not only the provider adapter) verifies `propose_changes` is permitted, checks `request_verification` when verification is requested, and resolves every requested verification ID against the consumer-owned registry **before applying any change**. Unknown checks or disallowed capabilities reject the proposal with the isolated worktree unchanged. A permitted proposal is snapshotted from the isolated worktree, normalized and policy-gated before apply.

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

## Windows fixture qualification — 2026-10-24

The hash-bound tests must create their declared LF bytes explicitly. Windows
text-mode writes and inherited `core.autocrlf=true` otherwise turn the fixture
into CRLF while the fake provider still proposes an LF hash. The executor
correctly rejects that stale basis; this is not a reason to normalize or weaken
its hash checks. Test fixtures now write exact bytes and disable line-ending
conversion only inside their temporary test repository. Explicit CRLF coverage
verifies preserved CRLF output and rejects an LF-to-CRLF change after a permit.

On the PR #47 stack at `395969ce9fc8db975e6d0fa31e92b7abb97da063`, the
Windows baseline reproduced three failures and five errors in 35 focused tests.
After fixture correction: 37 focused tests and 184 full repository tests without
failures; two symlink controls skipped because native symlink creation was
unavailable. Production harness modules and policy defaults are unchanged.

A separate manual local-model experiment used the existing llama.cpp client,
one real Qwen3.5-9B-Q6_K `fast64`/quick invocation, and a predeclared synthetic
JSON status-label correction. Existing routing, WorkerRequest/WorkerResult,
ChangeSet, isolated worktree, exact modify policy/permit and registered verifier
produced VERIFIED. The external verifier failed before the correction and
passed after; the original synthetic repository and local-AI configuration
remained unchanged. Model latency including the client was 5.438 seconds,
380 input / 175 output tokens. Only controller-owned verification code executed;
model output was data, not an executable program.

This is one bounded synthetic data-edit receipt, not a general coding benchmark,
an installed llama.cpp provider, a background coding queue or current-main
integration. Observed main `6a4346e54c15b7341b9bc355d07acfeb0ae66755` is not an
ancestor of the tested draft head. No merge, consumer update, dependency install,
paid call or permission expansion was performed. Full model/fixture evidence is
retained by the operator; no private machine paths or settings are published here.
