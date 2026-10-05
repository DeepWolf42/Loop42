# Evaluation

Loop42 evaluates its own development method with reproducible scenarios rather than self-description.

## Frozen scenarios

A frozen scenario captures:

- input project state/revision;
- task/request;
- available capabilities;
- protected boundaries;
- expected evidence requirements;
- acceptable outcomes and explicit non-goals.

The same scenario can be run across different harnesses or Loop42 revisions.

## Evaluation dimensions

Prefer observable measures:

- correctness of source-of-truth resolution;
- stale-state detection;
- defect/counterexample discovery;
- verified useful delta;
- unnecessary steps/retries;
- duplicated work;
- authority-boundary violations;
- provenance quality;
- recovery quality;
- token/time/tool-call overhead where measurable.

## Challenger tests

At least some scenarios should deliberately include:

- conflicting/old checkpoints;
- missing capabilities;
- misleading plausible assumptions;
- changed live head;
- redundant work requests;
- third-party/license ambiguity;
- incomplete evidence.

## Perturbation and recovery tests

For stepwise executors or computer-use adapters, include bounded perturbation cases in addition to clean-path success. Examples include an intentionally wrong but valid action, an unexpected selection/dialog state, a transient tool/app restart, or a stale/reordered observation.

Measure whether the system:

- detects that the observed state no longer matches the intended progression;
- chooses a bounded recovery such as cancel, undo, reselect, reconcile or stop;
- avoids compounding the error with invented state;
- leaves no unexplained residual objects/actions after recovery;
- can reproduce a replay only when the starting state, ordered action log and parameters are sufficiently bound.

Do not convert fault-injection success into a general robustness claim. Record the injected fault, exact scenario/runtime/version and the final independently checked result.

This pattern is informed by Biome-S1's explicit wrong-action injection and crash/replay evaluation at upstream revision `4a31bcfaca9b7ca5f5f1e2cb13be209e49532257`; Loop42 does not import its model/runtime or benchmark claims.

## Rule

Do not claim a model/harness/method is "better" without a defined scenario, baseline, and measurable result.
