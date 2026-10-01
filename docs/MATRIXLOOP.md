# Matrixloop

Matrixloop is Loop42's internal development method.

## Core loop

A bounded run should move through only the steps justified by the current problem:

1. **RECONCILE** — resolve live source of truth and detect stale assumptions.
2. **TARGET** — define one concrete product or infrastructure delta and confirm its **Execution Fit**: it is available with the actual capabilities, worth the cost/complexity, and can be carried out with the lowest reasonable operator friction.
3. **PRE-MORTEM** — identify realistic failure paths before implementation, including missing prerequisites, permissions, account/plan limits, hardware/tool availability, hidden cost and avoidable operator effort.
4. **IMPLEMENT / INSPECT** — make or inspect the smallest useful change.
5. **VERIFY** — run direct tests/evidence against the exact changed basis.
6. **FRICTION** — try at least one relevant counterexample or failure case.
7. **VALUE CHECK** — confirm the change produces useful delta, not only process.
8. **STOP / ITERATE** — continue only when another bounded pass has measurable value.

The loop is not a fixed ritual. Steps may collapse when evidence is already complete.

## Execution Fit

Before implementation or detailed operator instructions, check three things in order:

1. **Capability Fit** — Is the proposed path actually available with the current tools, permissions, account/plan, hardware, software and environment? Verify material prerequisites instead of assuming them.
2. **Value Fit** — Does the path materially serve the real goal relative to its cost, complexity, risk and maintenance burden? A technically possible route is not automatically a useful route.
3. **Operator Fit** — Among viable routes, prefer the lowest-friction option that still satisfies the goal and safety/quality constraints. Minimize unnecessary clicks, copy/paste, setup, repeated questions and manual recovery work.

If a material prerequisite is missing, do not walk the operator through downstream setup. Either choose a simpler viable fallback, surface the missing prerequisite, or stop that path. Do not recommend a paid upgrade or more complex architecture merely to preserve an already-started plan; first show why its added value justifies the cost and operator burden.

Detailed UI or command instructions should come **after** Execution Fit is established. See `docs/EXECUTION_FIT.md` and the frozen private-repository/paid-feature scenario.

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

Operator effort is also a real cost. Do not make the operator perform setup or navigation steps whose prerequisites, availability or expected value have not been established. Before creating another persistent task or agent role, try to complete the work in the current run, fold it into an existing coherent task, or delegate bounded preparation to a suitable local worker. Preserve spare capacity when possible.

## Operator sovereignty

Bounded autonomy reduces interruptions, not authority. Protected decisions remain with the operator: cost-bearing actions, publication/release, repository visibility, real machine actions, safety/quality boundary changes, destructive or materially irreversible actions, and major product-direction changes outside the authorized goal.

## Single-writer principle

Concurrent workers may inspect in parallel, but persistent changes must reconcile against the current live head before writing. A stale worker must stop/reload rather than replay work onto a moved target.

## External reviewers

Independent models/reviewers may challenge the system, but their findings are hypotheses until reproduced against the current source of truth. They never become a second authority automatically.


## Named evidence and gap checks

[`/truth` and `/gaps`](TRUTH_AND_GAPS.md) expose the existing reconciliation, target-selection and verification checks as bounded agent workflows. Use them within the stages above, reusing current evidence rather than adding another loop. They are not native executable host commands. Consumer adoption remains subject to exact-revision binding.

## External pattern scouting

Before inventing substantial new infrastructure or orchestration, Matrixloop may run a bounded external pattern scout. A scheduled maintenance scout may also look for newly useful patterns without blocking normal product work.

Scouting is an input to TARGET / PRE-MORTEM, not another loop stage. Discovery does not authorize adoption: relevance, project fit, expected value, provenance/license status and reproduction against the current source of truth still apply.

See `docs/EXTERNAL_PATTERN_SCOUT.md`.


## Hygiene / entropy control

Matrixloop maintenance may run a bounded hygiene pass when repositories,
workspaces or recovery surfaces accumulate stale references, completed branches,
superseded material or ambiguous duplicates.

Hygiene is **reconciliation, not deletion**. Fresh evidence may classify items
as active, historical, superseded, merged branch, duplicate candidate, orphaned,
stale reference or unknown. Classification is not authority to delete or move an
item. Destructive cleanup remains a separate protected action under the
consumer's retention and action-policy rules.

Do not infer a duplicate from a matching filename, infer an orphan from a
partial scan, or infer disposable state from age alone. Historical and frozen
compatibility material may be intentionally retained. Missing, stale or
incomplete evidence stays unknown.
