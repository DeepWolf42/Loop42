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
- `NOT_APPLIED`: the exact pre-action fingerprint is still present. The action
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
