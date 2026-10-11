# Optional executable completion gates

Status: opt-in experiment / candidate, not a default stop hook or replacement for Matrixloop acceptance review.

## Problem and scope

A correctly matched SUCCEEDED worker result proves transport and task lifecycle, not that every engineering acceptance criterion passed. Loop42 already has live-revision reconciliation, two-axis review and CI. Use a small executable gate set only for multi-step or correctness-sensitive deliveries where a missing final check is a realistic risk. Do not create one for trivial edits.

This Python standard-library checker lives in tools/checks/completion_gates.py. It is not the unlazy package. It executes no check commands without the explicit --run argument.

## Contract and invocation

Example gates.json, with the repository root as the command working directory:

~~~json
{
  "schema": "loop42.completion-gates.v1",
  "gates": [
    {
      "id": "regression",
      "criterion": "The checked-in regression suite passes on this exact source revision",
      "argv": ["python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
      "expect_line": "OK",
      "timeout_seconds": 180
    }
  ]
}
~~~

The caller supplies the **40-character full candidate SHA from a trusted task/CI context**. Do not store a commit's own SHA in its committed manifest (circular pin).

~~~text
python -m tools.checks.completion_gates gates.json --repo . --expected-revision EXACT_40_HEX_SHA
python -m tools.checks.completion_gates gates.json --repo . --expected-revision EXACT_40_HEX_SHA --run
~~~

The first command displays the checks without executing them; it intentionally returns nonzero (complete=false). Inspect every argv and every script it calls before using --run.

The second executes checks sequentially and returns success only if all processes exit 0 and print their exact expected line. The JSON report binds Git HEAD, a SHA-256 of the complete gate definition, and per-gate status/output fingerprint. There is no durable approval store or separate task list. Tracked worktree cleanliness and HEAD are checked before execution and after each gate. Stale, malformed, timed-out or missing evidence fails closed.

## Limits and safety

- **Not a sandbox.** The chosen command runs with the calling user's privileges, inherited PATH and environment. Avoid unreviewed command manifests, scripts, or executable dependencies. Direct argv avoids shell interpolation, but it is still arbitrary code execution when the command is executable.
- An uninformative command that prints OK may pass despite proving nothing. Requirement fit must still be reviewed independently and the check must be challenged with a relevant negative control.
- Dependencies outside tracked source, ignored/untracked files, external state, subprocess descendants and races between checks are not independently attested. Successful gates are not proof of physical reality or semantic acceptance.
- This checker is not a Stop hook, auto-merge permission, new worker queue, consumer pin update or authorization for printer, release or publication actions.
- Use it only when evidence value exceeds added operator/runtime friction; normal tests and Matrixloop remain primary.

## Controlled experiment (2026-10-11)

Baseline: DeepWolf42/Loop42 main at 2ec351ec6ddc9dba455e8e75930e9aaee8dbe7c6. Its worker reconciler intentionally distinguishes valid terminal task/attempt results without executing engineering acceptance checks.

An isolated synthetic Git fixture covered gate success, a simulated CORA-like invalid selector, missing expectation despite zero exit, inspect-only mode, wrong SHA, dirty tracked source, a self-modifying gate, one failed gate among two, malformed/duplicate manifest definitions and a changed definition digest. An additional 11th regression test copies the **real Loop42 worker implementation and its existing tests** into a disposable Git repository. It confirms an unmodified exact commit passes, then commits an intentional revision-identity bug; the same worker gate rejects that changed commit.

The actual Loop42 pull request runs a committed two-gate manifest, `tests/frozen_scenarios/loop42_completion_gates_v1.json`, against the exact GitHub Actions checkout SHA. The first gate executes the **real** worker-reconciliation regression suite; the second executes the completion-gate positive/negative tests. On candidate commit `986c67ca3f6c234f5a1e8151e4e241ed27897a6c`, CI run [#152](https://github.com/DeepWolf42/Loop42/actions/runs/38123878139) reported **128 tests passing and both completion gates PASS**, and the parallel [secret scan](https://github.com/DeepWolf42/Loop42/actions/runs/38123878182) passed. CI's gate receipt binds to the actual checked-out synthetic PR merge SHA `e5a7808581fd2c851c981fab6d851a16843e115e`; it must not be represented as the source PR head SHA.

The integrated mechanism demonstrates bounded fail-closed behavior against a **real Loop42 source mutation**, not a measured productivity improvement. It does **not** reproduce the historical CORA parser defect in real CORA code, prove semantic correctness of user-authored gates, or change CORA's pinned Loop42 revision. Publication, branch merge and consumer adoption remain separate protected actions.

## Provenance

Inspired by runnable-gate principles from Leonxlnx/unlazy, https://github.com/Leonxlnx/unlazy, upstream revision 16671491f6679ad9378f52604d3bc2415b4120c7 (MIT). The implementation is independently written in Python standard library; no unlazy source code, hooks, npm dependency or runtime code is copied.
