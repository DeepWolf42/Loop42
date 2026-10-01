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
