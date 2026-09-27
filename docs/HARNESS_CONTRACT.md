# Harness Contract

Loop42 separates its generic method from any single AI model, chat surface, local model, IDE, or automation host.

## Required harness capabilities

A harness may participate only through explicit capabilities such as:

- read current project sources;
- report exact source/revision identity;
- perform bounded edits;
- run or inspect verification;
- return structured results;
- preserve provenance;
- respect stop/authority boundaries.

Capability absence must remain explicit. A harness must not pretend to have performed an action it cannot perform.

## No hidden authority

Model output is never execution authority by itself.

A harness may not silently:

- merge/release/publish;
- operate physical machinery;
- purchase;
- overwrite protected truth;
- convert uncertain evidence into verified fact.

Those actions require the consumer project's own authority policy.

## Adapter rule

Provider-specific behavior belongs behind thin adapters. Generic Matrixloop rules must not depend on one vendor's prompt syntax, UI, context window, or proprietary feature.

## Context rule

A harness receives the smallest complete current context needed for the task. Context snapshots should be hash/revision bound where practical and must not be treated as fresher than their source.
