# Gap & Reuse Preflight

Status: **opt-in read-only CLI**, not an autonomous scout, slash command, scheduler, new Matrixloop stage, or approval authority.

Invoke from an existing git checkout during the host's **RECONCILE / TARGET** step for meaningful new architecture, infrastructure, repeated failures, dependency decisions, or scheduled maintenance:

```bash
python -m tools.checks.gap_reuse_preflight --repo . --target "checkpoint recovery" --trigger architecture --expected-head "$(git rev-parse HEAD)"
```

Routine work uses `--trigger routine` and **skips** the scan. Other triggers: `new_infrastructure`, `repeated_failure`, `dependency_decision`, `scheduled`.

The tool reuses `tools.context.repository_map` to inspect tracked working-tree paths/symbols, bind the report to HEAD and a map fingerprint, and produce at most three *possible* reuse leads. A matching symbol is not proof the implementation works or is suitable. Without an explicitly selected adapter it stays offline. It does not inspect installed tools, search external patterns, or execute suggested changes.

## Optional live open-work adapter

For a substantial dependency/capability decision, the host can use the same RECONCILE / TARGET call to collect open PR/issue leads instead of preparing an evidence file:

```bash
python -m tools.checks.gap_reuse_preflight --repo . --target "checkpoint recovery" --trigger dependency_decision --expected-head "$(git rev-parse HEAD)" --github-repository example/project
```

`--github-repository owner/name` explicitly selects the source on github.com; it is not inferred from remotes and is not proof that the selected source is the checkout's origin. The host owns that choice. The adapter runs only for non-`routine` triggers, after the initial HEAD/root check, and the preflight rechecks HEAD afterward. There is no registered host/chat hook or automatic background activation.

The standard-library adapter makes **one GET** to GitHub's [repository issues endpoint](https://docs.github.com/en/rest/issues/issues#list-repository-issues), which includes PRs. It reads at most 100 open records and 512 KiB with a 10-second socket timeout. No retries, pagination or redirects are followed. A pagination header, denied/rate-limited access, transport failure or invalid response produces `BLOCKED_UNKNOWN` and leaves the owned-code scan usable. Routine calls make no request even if the option is present.

It matches target keywords against **titles only**, returns at most eight metadata leads to the existing three-candidate selection, and checks that their URLs identify the selected repository. Bodies, comments, patches and retrieved instructions are not interpreted or executed. `CHECKED_NO_DELTA` means no keyword match in the complete returned title list, not absence of useful code or work. Titles are untrusted data; current PR head, implementation and suitability still need independent inspection. A selected repository can change after the timestamp; the local revision binds the observation to this preflight, not the remote work's immutable state.

Public sources work anonymously. If already supplied by the host, `GITHUB_TOKEN` is used only for this explicitly selected call; the tool neither obtains credentials nor changes permissions. It never returns token values, raw API bodies or exception text. Do not pass secrets in target text or commit private reports. A host with an existing connected repository tool can continue supplying `--evidence` instead; supplying both a live adapter and `open_work` evidence is rejected rather than silently overwriting either observation.

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

**Still missing for autonomous operation:** host-side trigger dispatch, installed-tool inventory, bounded external pattern search adapters, actual consumer acceptance tests. The optional live GitHub adapter is an on-demand title probe, not autonomous scouting or a reuse/merge approval.
