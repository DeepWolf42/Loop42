# Frozen scenarios

Reusable Loop42 evaluation scenarios live here.

Scenarios must pin their input basis and distinguish verified evidence from simulated fixtures. CORA-specific scenarios may be mirrored here only after their generic boundary is explicit.

## CORA context/harness equivalence v1

`cora_context_equivalence_v1.json` freezes the first extracted generic Factory surface against:

- repository: `DeepWolf42/C.O.R.A.`
- revision: `665bdd49724f27258ca4633b0dc5fa8fbb9ae602`
- `tools/project_context.py` blob: `4d187d6c840b7247fc43ebb98ee288eed6eac1ab`
- `tests/test_project_context.py` blob: `a994328aaba9b86df43774c845838e9ed7e92eac`
- `docs/CORA_FACTORY_MATRIXLOOP.md` blob: `a355c96a89938caad6ff82fbd200295a5aeddeef`
- `docs/CHATGPT_FIRST_ARCHITECTURE.md` blob: `1cbad4b85822a8ce60757ee06427f06256e33ac0`

The suite verifies only the generic boundary: exact/deduplicated context capture, stale-basis rejection, safe source paths, checkpoint replay/writer guards, bounded local-model transport, no second product truth, Matrixloop stop behavior and external-reviewer non-authority.

CORA product state, Arthur, printer/slicer/material/HIL behavior and CORA Recovery ownership are explicitly outside this frozen suite.

## Deviation rule

A frozen failure is treated as a regression unless the behavior change is explicit, the expected scenario is deliberately revised, and affected consumer evidence is re-run against the new exact revision. Passing a frozen suite never authorizes automatic deletion of predecessor material.

## Execution Fit: private repository / paid feature v1

`execution_fit_private_repo_paid_feature_v1.json` freezes a generic operator-friction regression:

- a feature's configuration UI is visible;
- effective enforcement requires an entitlement the current environment does not have;
- a simpler fallback exists;
- the method must verify prerequisites before asking the operator to perform downstream setup.

The expected behavior is Capability Fit -> Value Fit -> Operator Fit: detect the blocked paid route, stop it before setup, evaluate whether an upgrade is justified, choose the lowest-friction viable fallback and only then give actionable operator instructions.

The fixture is simulated. It preserves the decision failure mode, not a claim about any provider's current plan details.

## Execution Fit: limited task capacity v1

`execution_fit_limited_task_capacity_v1.json` freezes the rule that overlapping monitoring/work should be compressed before scarce persistent task capacity is consumed. It also preserves operator sovereignty for protected decisions.

## External pattern scout v1

`external_pattern_scout_v1.json` freezes bounded external scouting: candidates must be problem-linked, provenance-aware and value-checked rather than adopted because they are popular.

## Agent transcript evaluation v1

`agent_transcript_eval_v1.json` freezes a simulated stale-context/capability trap for the provider-neutral transcript evaluator. The expected route is to read current state first, inspect the relevant capability, avoid unjustified duplicate calls, cite returned evidence, and expose uncertainty or unavailability in the final answer.

The scenario pins Loop42 `2ec351ec6ddc9dba455e8e75930e9aaee8dbe7c6`. Its fixture is synthetic and proves only evaluator behavior. A real harness/model quality claim requires a separately captured real run bound to exact harness/model/version and scenario identity.
