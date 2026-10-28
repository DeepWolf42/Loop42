# External Pattern Scout

Status: proposed generic Loop42 workflow  
Canonical language: English

## Purpose

Loop42 should periodically look outside itself before reinventing infrastructure, workflow mechanics, safety gates, recovery logic, observability, or agent orchestration.

The goal is not trend chasing. The goal is to discover small, reusable patterns that can reduce risk, complexity, operator effort, or duplicated work.

External scouting is an input to Matrixloop, not a new source of truth and not a new loop stage.

## When to scout

Run a bounded scout when at least one of these is true:

- a new architecture or orchestration mechanism is being designed;
- the project is about to build infrastructure that likely exists elsewhere;
- a repeated failure suggests that another project may already have a proven pattern;
- a dependency/provider choice is being reconsidered;
- a scheduled maintenance pulse is due.

Do not block ordinary product work merely because no recent scout exists.

## Search breadth

Search for the **problem**, not only for projects that look like Loop42.

Start with the user's or project's literal terms, then deliberately expand into
synonyms, mechanisms and adjacent disciplines. A useful candidate does not need
to describe itself as an AI agent, loop or orchestrator if it solves the same
failure mode.

Useful search families include:

- AI / agents / prompts / context engineering / memory / evals / graders;
- durable workflows / state machines / checkpoints / replay / reconciliation;
- distributed systems / idempotency / optimistic concurrency / leases / fencing /
  event sourcing / saga / outbox;
- queues / workers / supervision / retry / circuit breaker / dead-letter handling /
  backpressure / bounded concurrency;
- incremental build systems / dependency graphs / invalidation / content-addressed
  state / reproducibility / caching;
- policy / provenance / attestations / audit / authorization;
- fault injection / chaos engineering / model checking / property-based testing;
- relevant domain control systems when the consumer problem maps to them.

A scout should sample across relevant families instead of repeatedly searching
minor variations of one product category. Keyword expansion is a discovery
heuristic, not permission to create a larger backlog.

A similar product is neither required nor sufficient. Prefer the smallest
transferable mechanism that addresses the current problem.

## Perspective probe

When uncertainty, repeated failure, or a substantial design choice justifies it,
the scout MAY spend one bounded pass reframing the problem before selecting
candidates. Use only the lenses that can change the search or pre-mortem:

- **downstream lens** — if the current plan succeeds, what becomes the next
  bottleneck, invalidated assumption, or operator burden?
- **inversion lens** — which central assumption would make the current framing
  wrong, and can removing or reversing a dependency expose a simpler route?
- **outside lens** — how would an operator, maintainer, safety reviewer, or
  adjacent discipline describe the same problem?

The probe produces at most one or two concrete alternate hypotheses or search
directions. It is not a brainstorming quota and MUST be skipped when it adds no
distinct decision, evidence target, or failure hypothesis.


## Gap detection and reuse gate

Before substantial new infrastructure, an important workflow change, or a repeated
failure, run **one bounded gap-and-reuse probe inside RECONCILE / TARGET**.
This is part of the existing Matrixloop and /truth-/gaps workflow, **not a new
loop stage**, agent, scheduler, database, permission or source of truth.

1. **Reconcile first.** State the agreed target, acceptance criteria, live
   source/revision, current implementation, existing work (issues, PRs, branches),
   previous research and relevant capabilities already provided by installed tools.
   Design intentions, drafts and passing tests on older revisions are not current
   integrated behavior.
2. **Map a small scope.** Sample the affected end-to-end workflow and failure
   modes rather than searching only the first named library or API. Include the
   operator-facing path, security, recovery and dependency/license impact where
   relevant; do not audit every product area on every invocation.
3. **Label search coverage honestly.** For each relevant slice distinguish
   `CHECKED_NO_DELTA` (searched on the stated basis; no useful improvement),
   `USEFUL_CANDIDATE` (grounded alternative worth evaluation),
   `NOT_SEARCHED` (coverage gap), and `BLOCKED_UNKNOWN` (required source,
   capability or evidence unavailable). **NOT_SEARCHED is not NO_USEFUL_DELTA.**
   A missing source is not a negative finding; record the limit and stop that
   dependent claim.
4. **Check reuse before invention.** Compare the current owned implementation,
   still-open work, supported existing-tool features and newly released plugin/
   SDK capabilities with small external patterns. Also sample an adjacent
   discipline or real user/operator failure if it may change the decision.
   Prefer `REUSE_EXISTING` or `SMALL_ADAPTER` over a replacement framework.
5. **Prioritize and stop.** Rank at most a few material blind spots by impact,
   safety/correctness, likely saved effort, cost and uncertainty. Select the
   smallest reproducible counterexample or compatibility test, or record a
   bounded `NEEDS_RESEARCH` follow-up. Respect the scout's candidate and
   time/run budgets; do not create backlog merely to fill a coverage matrix.

The output is a small **coverage delta**, not a global completeness claim:
checked scope and revision; highest-impact missed search angle; evidence/source
and freshness; what already works internally; best reusable alternative;
adoption/verification cost; explicit unknowns; recommended next test or
`NO_USEFUL_DELTA`. Reuse previous valid coverage when its dependencies have
not changed. Do not silently promote a design, open PR, benchmark claim or
unverified idea to integrated capability. Consumer-specific findings stay in
the consumer's authoritative records. The scout only proposes patterns;
implementation and any operator-owned action retain their normal gates.

## Scout contract

A scout must be bounded by:

- a clear problem statement;
- a freshness window appropriate to the topic;
- a small candidate limit;
- a time/run budget;
- explicit stop conditions.

For each candidate record:

1. source/project and exact revision or dated reference when available;
2. the concrete Loop42 or consumer problem it might help;
3. the pattern worth borrowing;
4. what must **not** be copied or assumed;
5. license/provenance status for any code-level reuse;
6. evidence level: VERIFIED_SOURCE, PLAUSIBLE_PATTERN, or NEEDS_VERIFICATION;
7. expected value versus adoption cost.

## Adoption gate

Discovery is not adoption.

A candidate may influence implementation only after it passes:

1. **relevance** — it addresses a current problem rather than adding novelty;
2. **fit** — it respects the current source of truth, authority boundaries, and provider portability;
3. **value** — expected benefit is proportional to new complexity and maintenance;
4. **provenance** — copied/adapted code has exact source and license review;
5. **verification** — the borrowed pattern is reproduced against the current project before being treated as useful evidence.

Architectural ideas may be reimplemented independently when no code is copied. Direct code reuse requires the normal third-party provenance and license gate.

## Output

A useful scout produces one of three outcomes:

- **ADOPT_CANDIDATE** — a bounded pattern is worth testing in Matrixloop;
- **PARK** — interesting but not justified now;
- **NO_USEFUL_DELTA** — nothing found that beats the current approach.

A scout must not create work simply because candidates exist.

## Anti-patterns

Do not:

- import frameworks only because they are popular;
- copy code before license/provenance review;
- treat stars, benchmarks, blog claims, or model confidence as proof of project fit;
- let external projects redefine consumer product truth;
- turn scouting into an unbounded research backlog;
- repeatedly rediscover the same rejected pattern without new evidence.

## Relationship to consumers

Loop42 owns the generic scouting method. Consumer projects decide whether a discovered pattern is relevant to their own domain.

CORA, for example, may borrow a generic checkpoint or authority pattern without importing another project's product semantics, printer assumptions, or safety claims.

## Executable opt-in preflight

A bounded, read-only local check is now available as `python -m tools.checks.gap_reuse_preflight` (see [Gap & Reuse Preflight](GAP_REUSE_PREFLIGHT.md)). A host must explicitly invoke it inside RECONCILE / TARGET; it does not search the web or auto-run for every change. Unavailable GitHub/open-work, installed-tool and external-research evidence stays `NOT_SEARCHED` until an authorized adapter supplies it. This CLI is not a complete autonomous scout or an adoption approval.
