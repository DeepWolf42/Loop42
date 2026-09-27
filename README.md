# Loop42

<p align="center">
  <img src="docs/assets/loop42-mark.webp" alt="Loop42 retro emblem" width="300">
</p>


Loop42 is a reusable development and factory system for building complex projects with AI-assisted workflows while keeping execution bounded, evidence-driven and recoverable.

Its internal method is the **Matrixloop**: a compact loop for reconciling live state, choosing one useful target, implementing or inspecting it, verifying the result, challenging it with realistic counterexamples, and stopping when another pass would add no measurable value.

## What Loop42 does

Loop42 provides generic development mechanics for:

- bounded iteration and explicit stop rules
- source-of-truth and stale-state handling
- recovery and reconciliation
- single-writer / live-head guards
- harness capability contracts
- prompt and skill evaluation
- run budgets and stop receipts
- provenance and third-party license gates
- GitHub visibility and freshness checks
- reusable context and navigation helpers
- frozen-scenario evaluation
- candidate learning and controlled evolution

## Design principles

**Evidence over confidence.**  
Claims should be tied to reproducible evidence, exact revisions, or clearly marked uncertainty.

**One truth, many workers.**  
Multiple models or tools may inspect and challenge a project, but they do not create competing authoritative states.

**Bounded autonomy.**  
Automation may do useful work inside explicit authority limits. Missing capability or evidence must stay visible rather than being guessed away.

**Useful delta over process.**  
The loop exists to improve the project. A check or iteration that produces no distinct decision, evidence, defect discovery or implementation value should be merged, simplified or stopped.

**Recovery by design.**  
Work should be resumable from explicit current state, accepted decisions, verified results and open blockers.

**Portable by default.**  
Provider-specific behavior belongs behind thin adapters. Matrixloop rules should not depend on a single AI vendor, IDE, chat surface or local model.

## Matrixloop in one line

`RECONCILE → TARGET → PRE-MORTEM → IMPLEMENT/INSPECT → VERIFY → FRICTION → VALUE CHECK → STOP/ITERATE`

The sequence is not a ritual. Steps may collapse when the required evidence already exists.

## Repository structure

- `docs/MATRIXLOOP.md` — Matrixloop lifecycle and stop rules
- `docs/HARNESS_CONTRACT.md` — reusable harness capability boundary
- `docs/CONSUMER_PROFILE.md` — exact-revision consumer binding contract
- `docs/RECOVERY_AND_TRUTH.md` — truth, stale-state and recovery rules
- `docs/EVALUATION.md` — frozen-scenario and method evaluation
- `docs/LICENSE_POLICY.md` — current licensing policy
- `THIRD_PARTY.md` — external source and provenance ledger
- `tools/` — reusable harness, context and verification utilities
- `tests/frozen_scenarios/` — reproducible evaluation scenarios
- `adapters/` — consumer integration examples

## Consumer projects

Loop42 is project-agnostic. Consumer projects keep their own product state, domain rules and authority boundaries and may pin an exact Loop42 revision/profile.

CORA is the first consumer project, but its product truth remains outside this repository.

## Status

Private development repository.

The **v0.1 extraction / consumer-binding foundation is verified**. Reusable context/harness mechanics, frozen CORA equivalence and the exact-revision consumer-profile contract are in place. Milestone issue #4 is closed; repository contracts and tests remain authoritative.

CORA currently pins verified Loop42 revision `de5be0fa5e085d63c8f98fe683f9936828478dbf`. That pin is intentionally exact and does not float when Loop42 `main` advances.

No root project LICENSE is intentionally present. A publication or distribution license will be chosen only after a release-specific dependency, file and license audit.

<details>
<summary>Why 42?</summary>

Because good systems need bounded loops, honest evidence, recoverable state —  
and occasionally the right question before the right answer.

</details>

