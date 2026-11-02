**English** · [Deutsch](CODEX_PROVIDER_OUTPUT.de.md)

# Codex proposal completion and handoff diagnostics

A proposal file alone must not authorize a ChangeSet. The local Codex adapter
accepts a proposal only after one complete, consistent CLI JSON event stream.
This is an adapter acceptance condition; registered verification and the existing
policy, dispatch, scope and receipt checks remain mandatory.

## Accepted completion

- One thread and one started turn, followed by one completed final agent message
  and one successful `turn.completed`.
- Only reasoning and agent-message items. Tools, errors, failed turns, unknown
  events, duplicate/unfinished items and activity after completion are rejected.
- The final message and output file must contain the same parsed JSON proposal.
  JSON formatting/key order may differ; JSON types and values must match.
- Existing ChangeSet validation still checks the actual schema, paths, hashes
  and requested verification. Stream completion does not make model text true.
- Missing usage remains unknown. Present token counts must be nonnegative
  integers, excluding booleans; no zero usage or monetary cost is inferred.

The existing process runner retains its deadline, output cap and descendant
containment. The adapter reads at most2MiB+1 proposal bytes; the accepted trace
is bounded to1MiB and4096 nonempty lines. No new process runner, dependencies,
daemon, background retry or credentials are introduced.

## Failures and recovery

Malformed/oversized proposals and inconsistent event streams return a failed
WorkerResult with a fixed `codex:CLI_*` code. The existing handoff records it as
`FAILED_WORKER` before applying changes. Repeating that task ID retrieves its
stored result, not another provider call. Ambiguous interruptions retain the
existing UNKNOWN/no-replay behavior. Raw CLI diagnostic text is not copied into
the worker rationale or human display.

Examples: `codex:CLI_INCOMPLETE_TURN`, `codex:CLI_REPORTED_FAILURE`,
`codex:CLI_PROPOSAL_MISMATCH`, `codex:CLI_INVALID_PROPOSAL`. Inspect the local
saved result and reconcile the cause before considering a separately authorized
new attempt. These codes grant no new retry, commit, push or merge authority.

## Operator output

JSON remains the default. Existing status values and exit codes remain0 for
`DONE_VERIFIED`,3 for unsuccessful stored results,2 for input/runtime errors.
Preflight errors retain their exception-class `reason` and add a bounded
`diagnostic_code`, including `STALE_SOURCE_REVISION`, `SOURCE_NOT_CLEAN`,
`COMMIT_NOT_AUTHORIZED`, `TASK_ID_CONFLICT` and `INVALID_INPUT_SHAPE`.

For German human-readable output, add `--human` to either operation:

```text
python -B -m tools.harness.handoff_cli status --input request.json --profile project.local.json --human
```

This format displays fixed explanations and a syntactically valid candidate hash,
never arbitrary model rationale. Machine consumers should keep using default JSON.

## Verification and limits

Regression tests cover incomplete/failed/ambiguous streams, proposal mismatch,
invalid JSON/usage, forbidden tool items, durable failed-attempt retrieval and
CLI compatibility. Deterministic process fixtures are labeled test doubles.
A real CLI compatibility trial is separate from these tests.

The existing runner now offers optional `separate_stderr=True`, used only by this
adapter. Its default combined-output behavior and result schema are unchanged.
Both streams share one output budget and process scope; stderr is bounded and
drained but never interpreted as proposal events or returned in the rationale.
The runner still decodes UTF-8 with replacement, so this establishes no byte-level
stdout attestation. Non-JSON data in stdout fails closed; an unsupported CLI/event
format needs explicit requalification instead of silent acceptance. A valid stream is not a source
attestation, privacy sandbox, signed receipt or general model-quality guarantee.

Official interface reference, checked2026-11-01:
[Codex non-interactive JSON output](https://learn.chatgpt.com/docs/non-interactive-mode).
