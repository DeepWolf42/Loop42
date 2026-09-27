# Loop42

Loop42 is the reusable development/factory system extracted from the CORA project.

**Matrixloop** is Loop42's internal method: a bounded, evidence-driven development loop for working across AI/harnesses without creating parallel project truth.

## Purpose

Loop42 owns generic development mechanics such as:

- bounded loop lifecycle and stop rules
- source-of-truth / stale-state / single-writer mechanics
- recovery and reconciliation
- harness capability contracts
- prompt/skill evaluation
- run budgets and stop receipts
- provenance and third-party license gates
- GitHub visibility/freshness guards
- reusable context/codemap mechanics
- frozen-scenario evaluation
- generic candidate-learning/evolution gates

Loop42 does **not** own product-specific state for CORA or any other consumer project.

## CORA boundary

- **CORA** = manufacturing product, product code, Arthur/Decision Compression, UI/product contracts, printer/slicer/material/HIL integrations and CORA-specific Recovery/state.
- **Loop42** = reusable Factory/development system.
- **Matrixloop** = the internal loop/method implemented by Loop42.

CORA may consume an exact Loop42 revision/profile. Loop42 must never become a second CORA product truth.

## Migration rule

The split from CORA is an **extraction + verification**, not a cleanup pass.

Nothing working is deleted from CORA merely because an equivalent Loop42 artifact exists. Generic material is copied/extracted first, Loop42 is independently verified, CORA is bound to an exact Loop42 revision, frozen CORA Factory scenarios are compared, and only then may old duplicated material be separately archived or deprecated.

## Repository status

Private development repository.

No root project LICENSE is intentionally present. A publication/distribution license will be chosen only after a release-specific dependency/file/license audit.

See:

- `docs/MATRIXLOOP.md`
- `docs/HARNESS_CONTRACT.md`
- `docs/RECOVERY_AND_TRUTH.md`
- `docs/EVALUATION.md`
- `docs/LICENSE_POLICY.md`
- `THIRD_PARTY.md`
