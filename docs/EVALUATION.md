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

## Rule

Do not claim a model/harness/method is "better" without a defined scenario, baseline, and measurable result.


## Opt-in refinement A/B review

A proposed agent instruction/skill is not useful merely because a model calls it a lesson. The standalone `tools/checks/refinement_trial.py` classifies *supplied* paired baseline/candidate outcomes with exact prompt, scenario, source, verifier and harness/model identity, plus required passing holdouts. This checker does **not** run a model, authenticate evidence or grant installation/merge authority. A genuine real-harness A/B run and independent artifact review are required before claiming improvement. See [Refinement Trial](REFINEMENT_TRIAL.md). No consumer pin updates automatically.
