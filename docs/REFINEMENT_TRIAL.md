# Evidence-bound refinement trial (optional)

**Status:** opt-in research/checker. No real model-quality improvement has yet been measured. This is NOT a persistent learning engine, automatic skill installer, extra Matrixloop stage or execution permit.

## Why

A coding agent may encounter a recurring error and suggest a reusable instruction. That does not prove the agent will improve; it may break unrelated, previously correct behavior. Loop42 already has frozen scenarios, exact-revision reconciliation, optional executable completion checks and action policy. This addition supplies only a small read-only classifier for paired, independently evaluated A/B results. It does not duplicate the transcript evaluator in open PR #41.

## Procedure

1. Confirm one repeatable failure that current contracts do not already address. Write one small reversible *supplemental* lesson.
2. Freeze target and at least one **previously passing** holdout scenario before running the experiment, plus a separate counterexample. Capture exact content and SHA-256 fingerprints.
3. Run the same real callable model/harness/version with identical scenario, source revision, permissions and environment. Change only the supplemental instruction. Prefer counterbalanced repetitions and record latency, usage and costs where available.
4. Evaluate actual outputs and transcripts with independent, scenario-appropriate verifiers, and preserve the underlying artifacts. Agent self-grading does not count as independent proof.
5. Supply a loop42.refinement-trial.v1 document to tools.checks.refinement_trial.evaluate_refinement_trial. Every arm binds source revision, prompt digest, scenario digest, verifier ID/revision, harness/model ID and a purported evidence digest. Missing observations must remain UNKNOWN.
6. Review actual verifier/trace/source artifacts **outside** this pure classifier. A positive classification permits investigation only. Durable instruction changes, new skills, releases, merge, CORA pin updates or physical-world actions require their separate authority and validation gates.

## Outcomes

- REJECT: any PASS -> FAIL paired regression.
- INCONCLUSIVE: any UNKNOWN, a holdout failing to preserve PASS -> PASS, or no FAIL -> PASS target improvement.
- PROMISING: at least one target FAIL -> PASS, every holdout PASS -> PASS, no regression or UNKNOWN. **Not** permission to adopt.
- Malformed input or a source, prompt, scenario, verifier, model or harness identity mismatch raises ValueError.

**Trust warning:** hashes here assert content identity only; they are not proof of execution or authentication. A caller could fabricate structurally valid PASS metadata. Do not treat checker output as a verification receipt, model-quality result, or independent oracle. The existing completion gates check actual engineering behavior and are not a replacement for semantic agent evaluation.

## First bounded actual experiment

Target: tests/frozen_scenarios/execution_fit_private_repo_paid_feature_v1.json (unusable paid setup). Holdout: tests/frozen_scenarios/execution_fit_limited_task_capacity_v1.json (preserve authority/task limits). Candidate lesson: "Verify actual availability/entitlement before recommending operator setup or upgrade. If blocked, stop that path and choose the lowest-friction viable fallback; missing evidence remains UNKNOWN."

Add at least one fresh, untouched holdout. Run the baseline without the supplemental lesson and the candidate with that lesson, under the *same* model and harness, and score them independently. PR #41 may later provide transcript statistics but these alone do not establish semantic correctness.

**Evidence status:** 20 synthetic decision-boundary unit tests passed locally during implementation. No real model/harness A/B run was performed; no productivity gain or CORA manufacturing benefit is claimed.

## Provenance

Pattern inspiration: PrimeIntellect-ai/prime-agent, upstream commit 2ee7e623a70d8ccd9c72ffc6c4f25be2cc1bc02d, MIT license (root LICENSE), especially README and skills/refine/SKILL.md. This Python-standard-library checker independently reimplements only a narrowly scoped, more restrictive review gate. No upstream code, assets, runtime or dependencies are imported. See THIRD_PARTY.md.
