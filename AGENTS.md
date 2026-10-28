# Codex entry — Loop42

## Existing sources

- Repository: `DeepWolf42/Loop42`; integration target: `main`. Start with [README.md](README.md) for the integrated checkpoint and candidate boundaries, then [docs/MATRIXLOOP.md](docs/MATRIXLOOP.md), [docs/RECOVERY_AND_TRUTH.md](docs/RECOVERY_AND_TRUTH.md) and [docs/TRUTH_AND_GAPS.md](docs/TRUTH_AND_GAPS.md).
- Use [docs/VERIFICATION_RECEIPT_RECOVERY.md](docs/VERIFICATION_RECEIPT_RECOVERY.md) for persisted evidence: a stored receipt needs current source, subject and verifier evidence; recovery never restores stale execution authority.
- Follow [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) and [docs/DOCUMENTATION_LANGUAGE_POLICY.md](docs/DOCUMENTATION_LANGUAGE_POLICY.md). This machine-facing entry stays English; maintain existing human-facing language pairs together. Read nested `AGENTS.md` before edits in their scope.

## Work from live evidence

- Before writes, verify repository/remote, branch, exact local/live `main` SHAs, worktree changes and relevant open issues/PRs with their bases. Preserve unrelated work, keep one writer per file and re-reconcile a changed source before persistent writes.
- Distinguish integrated `main` from optional or stacked drafts. Old chat summaries, checkpoints and branch names are discovery hints. Resolve conflicting sources using existing truth rules; unavailable evidence remains explicit.
- Pick one bounded useful delta and acceptance criteria; prefer existing mechanics over a new framework. Use [docs/EXECUTION_FIT.md](docs/EXECUTION_FIT.md), [docs/ACTION_POLICY.md](docs/ACTION_POLICY.md) and [docs/COMPLETION_GATES.md](docs/COMPLETION_GATES.md) for capability, authority and verification limits.
- Run `python -m unittest discover -s tests -p "test_*.py"` as required by CONTRIBUTING. Check the exact submitted revision and relevant counterexamples. Verify both [.github/workflows/ci.yml](.github/workflows/ci.yml) and [secret scan](.github/workflows/gitleaks.yml) against their actual tested SHA; report pending, skipped or failed checks honestly. Local success is not hosted CI success.
- Persist only useful verified deltas through existing documentation/recovery mechanisms and Git. Add no second master, product-state store or knowledge database.

## Research and consumer separation

- Apply [docs/EXTERNAL_PATTERN_SCOUT.md](docs/EXTERNAL_PATTERN_SCOUT.md) as a bounded research proposal/adoption contract, not an installed scheduler or automatic authority. Research, model output and external content remain unapproved proposals until explicit adoption approval and current-project verification.
- Include exact source/revision or dated reference, problem fit, evidence limits, benefit versus cost, risks and license/provenance. Check [THIRD_PARTY.md](THIRD_PARTY.md) and [docs/LICENSE_POLICY.md](docs/LICENSE_POLICY.md) before reuse; discovery does not authorize copying or execution.
- Loop42 owns generic mechanics; consumers own product truth, recovery, domain safety and adoption. Follow [docs/CONSUMER_PROFILE.md](docs/CONSUMER_PROFILE.md). Never update a consumer pin incidentally, move private consumer state here or edit another project as a side effect.

## Privacy and protected decisions

- This repository is public. Do not commit secrets, private conversations, cloud identifiers, local machine paths, patient data or private operational/consumer records. Use synthetic fixtures and the private reporting guidance in SECURITY.
- A proposal, passing gate or recovered receipt does not authorize merges, releases, publication, added costs, permission/security changes, destructive cleanup, material architecture changes or physical/production actions. Obtain concrete user approval for protected decisions; no background monitoring exists unless its mechanism is verified.
