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

## Prompt / model comparisons

A prompt or model change is not an improvement merely because the output reads
better. Record the exact prompt contract fingerprint and evaluate candidates on
the same frozen scenarios, acceptance criteria and observable measures. Keep
validation scenarios separate from prompt-tuning examples where practical.

## Recovery fault matrix

Recovery claims must include deliberate interruption and ambiguity cases, not
only happy-path replay. At minimum, the frozen recovery matrix should exercise
lost responses after an applied side effect, stale observations, partial terminal
artifacts, late results, duplicate workers, host loss after historic activity,
and safety-state changes between permit issue and side effect.

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
