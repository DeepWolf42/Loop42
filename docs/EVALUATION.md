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

## Real agent transcript evaluation

Frozen scenarios may also evaluate an actual harness/model run rather than only static contracts or deterministic helpers.

The provider-neutral transcript contract in `tools/evaluation/agent_transcript.py` separates:

- the exact scenario and Loop42 revision;
- harness/model identity;
- which observations the harness can actually capture;
- tool/capability calls and canonical argument identity;
- tool results, explicit errors and evidence identifiers;
- final answer text;
- token usage when the harness exposes it.

The evaluator reports routing, repeated identical calls, malformed/invalid requests, evidence citation, answer/uncertainty requirements and measurable overhead. Missing capture capability remains `UNKNOWN`; it is never inferred from another field.

Captured tool results must follow their own calls, and no tool activity may follow the final answer. When results are captured, pending results must finish before the answer. Independent calls may overlap and complete in a different order; missing result capture still remains `UNKNOWN`.

Evidence citations match complete identifiers rather than identifier prefixes. Whitespace, quoting and ordinary punctuation may delimit a citation; a terminal sentence full stop is allowed, while a dotted identifier extension is not the same evidence identifier.

Repeat policy belongs to the frozen scenario. An identical read may be wasteful in one scenario and a justified re-check after externally changed state in another. Loop42 therefore does not impose one global zero-repeat rule.

A transcript score is evaluation evidence only. It is not a verification receipt, model authority, tool authority, consumer-state mutation or proof that an uncaptured action occurred. A real-agent quality claim requires a real captured run tied to the exact harness/model/version and scenario basis; synthetic fixtures test the evaluator only.

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
