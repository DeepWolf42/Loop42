# Recovery and Truth

Loop42 defines generic recovery mechanics; each consumer project owns its own product truth.

## Truth hierarchy

For any consumer project:

1. identify the project's declared authoritative source(s);
2. resolve the live revision before work;
3. treat older snapshots/checkpoints as recovery aids, not automatically-current truth;
4. when sources disagree, apply the consumer project's precedence rules and mark unresolved uncertainty.

Loop42 itself must not become a second product-state store.

## Recovery checkpoint

A useful recovery record should contain:

- exact source/revision basis;
- accepted decisions;
- completed verified work;
- unresolved blockers;
- next bounded action;
- evidence/CI status;
- known stale or unknown assumptions.

## Stale-state guard

A worker that captured revision A must re-check before persistent write. If the live source moved incompatibly to B, stop/reconcile first.

## No-delete migration rule

Repository or architecture migrations are extraction + verification operations. Do not delete the predecessor merely because a copy exists. First verify the new authority and consumer binding; cleanup is a separate explicit decision.

## Recovery is not specification

Recovery documents summarize how to resume. They must not silently evolve into a competing implementation/specification authority.
