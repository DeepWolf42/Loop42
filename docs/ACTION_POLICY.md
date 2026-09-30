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
