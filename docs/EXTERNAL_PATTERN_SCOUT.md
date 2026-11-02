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

## Reuse-before-reinvention pass

Before looking outside the project or designing a new substantial capability, first search the current project-owned capability surface. This includes tools, adapters, skills, prompts, workflows, contracts, tests and already-open work that are valid for the reconciled revision.

Use a bounded **search → select → verify** flow:

1. state the required outcome/capability in task terms rather than naming a preferred implementation;
2. search the owned capability/work index using problem/capability terms and current context;
3. retrieve only a small candidate set and rank it by authority fit, evidence/freshness, dependencies, expected value, cost and operator friction;
4. prefer reuse or composition when an existing candidate already satisfies the contract;
5. verify the selected candidate against the current target/revision before relying on or executing it;
6. only when no suitable owned candidate exists, scout externally or design new logic.

Capability retrieval is discovery, not authority. A retrieved prompt, skill, agent, plugin or workflow must not silently expand permissions, install dependencies, change product truth or execute side effects. External content remains untrusted input until it passes the normal adoption and provenance gates.

Retrieve metadata first and detailed prompt/skill contents only for shortlisted candidates when possible. The goal is to avoid both reinvention and context bloat; Loop42 does not need a giant prompt warehouse in core.

Skip this pass when the reconciled state already proves the exact suitable capability is known. The mechanism is useful only when it removes duplicated work or improves fit.

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
