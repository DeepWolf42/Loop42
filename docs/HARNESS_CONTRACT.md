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


## Bounded worker dispatch and health evidence

A serial worker integration must reconcile existing queue, attempt, result,
error and archive evidence before a new submission. Every proposal task is bound
to a task ID, attempt ID, exact source revision, context fingerprint and explicit
acceptance criteria. At most one unresolved local attempt may exist for the
serial worker.

Host availability, worker health, task lifecycle and evidence freshness are
separate states. Missing or stale telemetry is not a failure and is not proof of
running work. A powered-off, sleeping, offline or sync-delayed host is therefore
UNREACHABLE/UNKNOWN until fresh evidence exists. A fresh host observation with
no worker is STOPPED. STALLED requires fresh host evidence plus an explicit
progress deadline; historic START text, an open Ollama port, model inventory or
GPU activity alone do not prove inference progress.

Completion requires a complete validated result or error record matching the
exact task, attempt, source revision and context identity. Late results,
conflicting attempts, duplicate worker sessions, partial terminal files, clock
skew and safety-stop markers block blind retry. Safety-stop state is latched by
the adapter/consumer and must never be auto-cleared by this contract.

Offline periods stay notification-silent. A notification is appropriate only
for a newly validated result, a newly verified actionable failure, or a new
state requiring operator review such as a conflict, late result or safety stop.

Provider-, Drive-, filesystem- and OS-specific observation/write behavior stays
in thin adapters. The generic reconciler never starts processes, writes queue
files, commits code, clears safety markers, or grants model output authority.
