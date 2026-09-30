# Harness tools

Provider-specific harness adapters live behind Loop42's generic capability and authority contracts.

## Local Ollama adapter

`ollama_worker.py` is a deliberately narrow local adapter. It consumes the exact snapshot produced by the generic context tool and grants the model **proposal-only** authority.

Inspect a request without networking:

```text
python tools/harness/ollama_worker.py --repo /path/to/consumer request --model YOUR_MODEL --prompt "What is the next evidenced step?"
```

Run one local request:

```text
python tools/harness/ollama_worker.py --repo /path/to/consumer run --model YOUR_MODEL --prompt "What is the next evidenced step?"
```

Boundary:

- plain HTTP loopback origin only;
- redirects refused;
- local model inventory checked before chat;
- missing models are refused rather than implicitly downloaded;
- non-streaming response only;
- Ollama structured outputs are requested with an explicit JSON schema and temperature 0;
- malformed, ambiguous or duplicate-key JSON is rejected instead of being treated as a proposal;
- the validated proposal uses bounded `summary / known / proven / open / discarded / next / evidence_paths` fields;
- the result records a SHA-256 of the exact proposal schema as well as the snapshot fingerprint and Git HEAD;
- model output cannot checkpoint, commit, push, publish or operate physical systems.

Consumer projects keep their own action/approval policy.

## Extraction provenance

The first adapter was extracted from CORA's guarded local Ollama worker at `DeepWolf42/C.O.R.A.` revision `665bdd49724f27258ca4633b0dc5fa8fbb9ae602`. Product-specific CORA instructions and result schema names were removed. The reusable network/capability boundary is preserved behind the Loop42 harness contract.


## Bounded worker reconciliation

`worker_dispatch.py` is the generic state/reconciliation layer for serial local
workers. Adapters provide structured host/session observations and queue/result
artifacts; the reconciler keeps these dimensions separate:

- host availability: AVAILABLE / UNREACHABLE / UNKNOWN;
- worker health: HEALTHY / STOPPED / STALLED / FAILED / CONFLICT / UNKNOWN;
- task lifecycle: IDLE / QUEUED / RUNNING / SUCCEEDED / FAILED / CONFLICT / BLOCKED / UNKNOWN;
- evidence freshness: FRESH / STALE / UNKNOWN.

Dispatch identity includes task ID, attempt ID, exact source revision, context
fingerprint and bounded acceptance criteria. A validated terminal result must
match all of them. Unresolved attempts, late results, conflicting terminal
evidence, duplicate workers and latched safety stops block a new submission.

The notification helper is transition-only: ordinary offline/stale observations
stay silent; new validated results, actionable failures and operator decisions
may notify once when the adapter persists the previous reconciled state.

This layer deliberately does not encode Drive paths, PowerShell process control,
Ollama service management or a second scheduler. Those remain adapter/consumer
concerns.


### Dispatch permits: recheck before the queue write

`issue_dispatch_permit(...)` creates a short-lived fingerprint only from fresh,
available host evidence and a currently empty/reconciled dispatch basis.
`validate_dispatch_permit(...)` must be called after any pause/approval and directly
before the adapter writes a new queue item. Queue/result changes, attempt reuse,
host-session changes, safety stops, stale telemetry or changed acceptance criteria
invalidate the old permit. A failed validation means stop and reconcile; it never
means "refresh and write anyway."


### Structured proposal boundary

The local model does not choose its own result shape. `ollama_payload(...)` sends
Loop42's proposal JSON schema through Ollama's documented `format` field and also
includes the schema in the prompt. `run_ollama(...)` parses and validates the returned
JSON again locally before producing `loop42.ollama-worker-result.v2`.

Schema enforcement is useful structure, not trust. A valid proposal is still
unverified model output. It does not prove its claims, satisfy worker-dispatch
task/attempt identity by itself, authorize checkpoint writeback, or grant any shell,
Git, network, printer or physical authority.

Streaming remains deliberately out of this generic adapter for now. The later local
Deep Thought/Drive adapter can use streaming as a fresh progress signal only when its
actual Windows worker lifecycle and heartbeat write are tested together; historic or
partial chunks must never be mistaken for successful completion.


## Action policy decision

`action_policy.py` is a pure pre-action decision boundary. A consumer describes
an action as read-only, reversible write, or protected and receives only
`ALLOW / ASK_USER / DENY`.

Read-only work defaults to ALLOW. Reversible writes default to confirmation.
Protected actions are never auto-allowed by ordinary policy rules. In headless
execution, any `ASK_USER` result becomes `DENY`.

Rules may narrow by exact action, target prefix, effect and execution mode with
explicit priorities; equal-priority conflicts fail closed. The module never
executes the requested action, never creates durable approval, and does not
replace dispatch-permit revalidation immediately before a write.
