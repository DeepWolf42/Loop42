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

## Rule

Do not claim a model/harness/method is "better" without a defined scenario, baseline, and measurable result.
