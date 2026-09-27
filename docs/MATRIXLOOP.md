# Matrixloop

Matrixloop is Loop42's internal development method.

## Core loop

A bounded run should move through only the steps justified by the current problem:

1. **RECONCILE** — resolve live source of truth and detect stale assumptions.
2. **TARGET** — define one concrete product or infrastructure delta.
3. **PRE-MORTEM** — identify realistic failure paths before implementation.
4. **IMPLEMENT / INSPECT** — make or inspect the smallest useful change.
5. **VERIFY** — run direct tests/evidence against the exact changed basis.
6. **FRICTION** — try at least one relevant counterexample or failure case.
7. **VALUE CHECK** — confirm the change produces useful delta, not only process.
8. **STOP / ITERATE** — continue only when another bounded pass has measurable value.

The loop is not a fixed ritual. Steps may collapse when evidence is already complete.

## Stop rule

Stop when:

- the requested delta is implemented and verified;
- another pass has no concrete new hypothesis or measurable expected value;
- required evidence is unavailable;
- authority would cross a protected boundary;
- the live source of truth changed and the run must reconcile first.

Do not manufacture additional work merely to keep the loop active.

## Anti-overhead rule

Process exists to improve the product or development system. If a loop/check produces no distinct decision, defect discovery, evidence, or implementation value, merge it into another step or remove it.

## Single-writer principle

Concurrent workers may inspect in parallel, but persistent changes must reconcile against the current live head before writing. A stale worker must stop/reload rather than replay work onto a moved target.

## External reviewers

Independent models/reviewers may challenge the system, but their findings are hypotheses until reproduced against the current source of truth. They never become a second authority automatically.
