# Action policy boundary

Loop42 consumers may need a small machine-readable decision before a tool or
adapter performs a side effect. This boundary converts the existing operator
sovereignty rules into a pure `ALLOW / ASK_USER / DENY` decision. It never
executes the action itself.

## Semantics

Actions declare one effect class:

- `READ_ONLY`: inspection/query only; default ALLOW.
- `REVERSIBLE_WRITE`: bounded reversible write; default ASK_USER.
- `PROTECTED`: spending, publication/release, visibility, physical machine
  action, safety/quality authority, destructive/materially irreversible action,
  protected product-state merge, or major product-direction change; never
  auto-allowed by a normal rule.

Rules may narrow by exact action, target prefix, effect and interactive/headless
mode. Highest priority wins. Equal-priority conflicts fail closed:
`DENY > ASK_USER > ALLOW`.

In non-interactive/headless execution, `ASK_USER` becomes `DENY`. A protected
action matched by an ALLOW rule is downgraded to `ASK_USER`, then to `DENY`
if no interactive operator is present.

This module is only a policy decision. It does not create durable approval,
perform a side effect or supersede the consumer project's own authorization.
Time-sensitive write/dispatch state still needs the existing pre-side-effect
revalidation permit.

## External pattern provenance

Gemini CLI's public policy-engine documentation at revision
`38700b4b38bf387dafded6c97c3f190d084b49e9`, file
`docs/reference/policy-engine.md` (blob
`95e65b33bd47e342c644b059e2e7a7c27d171d85`), documents the general
`allow / deny / ask_user` policy pattern, priority ordering, argument/context
matching and the fail-closed rule that user confirmation becomes denial in
non-interactive mode.

Gemini CLI is Apache-2.0. Loop42 independently implements only this narrow
general policy pattern in Python standard-library code; no Gemini CLI
implementation code or runtime is imported.


## Post-interruption side-effect reconciliation

A runtime ending after an action request is not evidence that the action failed.
For bounded side effects whose provider adapter can project the relevant target
state into a stable canonical fingerprint, consumers may record a
`SideEffectIntent` before execution and use
`tools/harness/side_effect_reconcile.py` after an interruption.

The intent binds one action ID, action, target and state-projection scope to
different pre-action and desired SHA-256 fingerprints. A fresh provider re-read
using the same target and projection scope is classified as:

- `APPLIED`: the desired fingerprint is present. Do not replay.
- `NOT_APPLIED`: the exact pre-action fingerprint is still present **and** the
  provider proves the original attempt cannot still complete. The action
  may be reconsidered, but the old policy result, approval and provider
  preconditions are not durable authority; evaluate them again before any write.
- `CONFLICT`: the target/scope differs or the target state has diverged. Do not
  replay; reconcile the new state.
- `UNKNOWN`: evidence is absent, stale, future-dated, incomplete or invalid.
  Do not replay.

The state projection is provider/consumer-owned evidence, not a second product
truth. It must be deterministic and narrow enough that equality proves the
relevant before/desired condition. If a deterministic postcondition cannot be
specified, leave the interrupted side effect unresolved instead of manufacturing
an `APPLIED` or `NOT_APPLIED` result.

This contract is pure classification. It never executes the action, never
persists approval and never turns `NOT_APPLIED` into automatic permission.

### In-flight requests and delayed observations

A fresh read can overtake an earlier write. A timeout, lost tool response,
runtime restart or cancelled chat does not prove that the provider cancelled
the request. Unchanged target state alone therefore returns `UNKNOWN` with
`prior_attempt_not_proven_quiescent`, and `may_reconsider` remains false.

The adapter may set `SideEffectObservation.quiescent_action_id` only after
provider evidence establishes that the exact `SideEffectIntent.action_id`
cannot produce a later effect (for example a terminal operation status or an
acknowledged cancellation/fence), followed by a coherent authoritative target
read. The ID must identify a unique attempt, not a reused task label. An old
attempt's proof cannot settle a new one. Absence in an eventually consistent
listing, elapsed time and the loss of the caller's process are not this proof.
If the provider cannot establish it, leave the attempt `UNKNOWN`; do not infer
failure or replay. Observing the desired state still suppresses replay without
claiming which actor caused that state.

Consumers persist intent/evidence through their existing Recovery authority;
this classifier does not create a journal or durable runtime. After restart,
rediscover available tools and read current authoritative sources before
classifying. Neither a remembered capability nor an old ALLOW result is proof
that a tool, permission or provider precondition still exists. DispatchPermit
remains the separate pre-queue-write check. These rules apply to Work and local
workers equally; adapter/end-to-end verification remains necessary.
