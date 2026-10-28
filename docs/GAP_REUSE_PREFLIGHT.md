# Gap & Reuse Preflight

Status: **opt-in read-only CLI**, not an autonomous scout, slash command, scheduler, new Matrixloop stage, or approval authority.

Invoke from an existing git checkout during the host's **RECONCILE / TARGET** step for meaningful new architecture, infrastructure, repeated failures, dependency decisions, or scheduled maintenance:

```bash
python -m tools.checks.gap_reuse_preflight --repo . --target "checkpoint recovery" --trigger architecture --expected-head "$(git rev-parse HEAD)"
```

Routine work uses `--trigger routine` and **skips** the scan. Other triggers: `new_infrastructure`, `repeated_failure`, `dependency_decision`, `scheduled`.

The tool reuses `tools.context.repository_map` to inspect tracked working-tree paths/symbols, bind the report to HEAD and a map fingerprint, and produce at most three *possible* reuse leads. A matching symbol is not proof the implementation works or is suitable. It does **not** search the internet, call GitHub issues, inspect installed tools, or execute suggested changes.

An authorized host adapter may supply researched evidence with `--evidence evidence.json`:

```json
{
  "open_work": {
    "status": "USEFUL_CANDIDATE",
    "source": "authenticated PR inventory",
    "checked_at": "2026-10-28T08:20:00+01:00",
    "revision": "<exact git HEAD>",
    "items": [
      {"name": "existing PR", "reference": "https://github.com/example/project/pull/12", "reason": "possible reuse"}
    ]
  },
  "installed_capabilities": {"status": "NOT_SEARCHED", "reason": "host inventory unavailable"},
  "external_patterns": {"status": "NOT_SEARCHED", "reason": "no research performed"}
}
```

Coverage labels: `CHECKED_NO_DELTA`, `USEFUL_CANDIDATE`, `NOT_SEARCHED`, `BLOCKED_UNKNOWN`. Missing evidence is **NOT_SEARCHED**, never a negative research result. Checked evidence needs a source and offset-aware timestamp; open work/tool evidence must match the exact HEAD or is downgraded to `BLOCKED_UNKNOWN`. Adapter-provided claims are not independently verified by this CLI.

Priority: existing code → open work → installed capabilities → external patterns. Output is structured JSON with scope, coverage, next action, fingerprint, and `adoption_authorized: false`. No edits, installs, approvals, consumer pin changes or merges are performed. The host must independently inspect and verify the recommendation through existing action-policy/verification gates.

**Still missing for autonomous operation:** host-side trigger dispatch, authenticated PR/issue queries, installed-tool inventory, bounded external search adapters, actual consumer acceptance tests. Do not claim automatic scouting until these are implemented and verified.
