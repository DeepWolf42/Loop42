**English** · [Deutsch](README.de.md)

# Loop42

<p align="center">
  <img src="docs/assets/loop42-mark.webp" alt="Loop42 retro emblem" width="300">
</p>

Loop42 helps long-running, AI-assisted development stay **understandable, verifiable and resumable**.

Instead of letting chats, tools, branches and workers slowly drift into different versions of reality, Loop42 keeps returning to a few simple questions:

**What is actually true now? What is the next useful thing to do? Are we allowed and able to do it? Did it really work? Is another round still worth it?**

## In plain language

Loop42 is **not** an AI model, a project-management app or a second database for your project.

It is a reusable **working method plus small tools** that help a project stay on one current truth while humans, AI models and automation work on it.

| Common failure mode | Loop42's response |
| --- | --- |
| Old chats or assumptions are treated as current | Reconcile against live sources first |
| Several workers create competing versions of the project | Keep one authoritative project state |
| Automation keeps going because it can | Use explicit authority, capability and stop limits |
| "Looks good" replaces proof | Require evidence, verification or visible uncertainty |
| Work is repeated after interruptions | Recover from explicit state, decisions and checkpoints |
| More process is mistaken for more progress | Stop when another pass adds no useful value |

## The Matrixloop

The internal method is called the **Matrixloop**. In human terms:

1. **Reconcile** — check the live state instead of trusting stale context.
2. **Choose one target** — pick the next useful, bounded piece of work.
3. **Pre-mortem** — look for obvious ways the plan could fail before spending effort.
4. **Implement or inspect** — do the work that is actually needed.
5. **Verify** — test the result against evidence.
6. **Check friction** — notice unnecessary setup, operator work or complexity.
7. **Check value** — ask whether another pass would create a real improvement.
8. **Stop or iterate** — continue only when there is a distinct reason.

Technical shorthand:

`RECONCILE → TARGET → PRE-MORTEM → IMPLEMENT/INSPECT → VERIFY → FRICTION → VALUE CHECK → STOP/ITERATE`

The sequence is a guide, not a ritual. Steps can collapse when the required evidence already exists.

## Core rules

**One truth, many workers.**  
A project keeps its own authoritative state. Models and tools may inspect, challenge and improve it, but they should not silently create competing truths.

**Evidence before confidence.**  
Important claims should point to reproducible evidence, an exact revision or clearly marked uncertainty.

**Bounded autonomy.**  
Automation may act inside explicit authority and capability limits. Missing access, evidence or capability stays visible instead of being guessed away.

**Useful change over process volume.**  
A loop that produces no new decision, evidence, defect discovery or implementation value should be simplified or stopped.

**Recovery by design.**  
Interrupted work should be resumable from explicit current state, accepted decisions, verified results and open blockers.

**Portable by default.**  
Provider-specific behavior belongs behind adapters. The method should not depend on one AI vendor, IDE, chat surface or local model.

**Execution fit before operator work.**  
Before handing setup steps to a human, check whether the path is actually possible, useful and worth the friction.

## Where Loop42 fits

Loop42 is project-agnostic. **Consumer projects keep their own product state.** Loop42 supplies the reusable working method and supporting mechanics around that state.

CORA is the first consumer project. CORA keeps its own product state and pins an exact verified Loop42 revision rather than automatically following every new commit on `main`.

## Start here

If you want to understand the system rather than read every file:

- [Matrixloop](docs/MATRIXLOOP.md) — the lifecycle and stop rules
- [Execution Fit](docs/EXECUTION_FIT.md) / [Deutsch](docs/EXECUTION_FIT.de.md) — can and should this work actually run?
- [Recovery and Truth](docs/RECOVERY_AND_TRUTH.md) — source-of-truth, stale-state and recovery rules
- [Harness Contract](docs/HARNESS_CONTRACT.md) — what an execution environment must be able to do
- [Consumer Profile](docs/CONSUMER_PROFILE.md) — how a project binds to an exact Loop42 revision

<details>
<summary>Technical reference and repository map</summary>

### Evidence, evaluation and external inputs

- `docs/TRUTH_AND_GAPS.md` / [Deutsch](docs/TRUTH_AND_GAPS.de.md) — bounded evidence and gap workflows
- `docs/EXTERNAL_PATTERN_SCOUT.md` / [Deutsch](docs/EXTERNAL_PATTERN_SCOUT.de.md) — bounded external pattern scouting
- `docs/EVALUATION.md` — frozen-scenario and method evaluation
- `tests/frozen_scenarios/` — reproducible evaluation scenarios

### Safety, publication and provenance

- `docs/LICENSE_POLICY.md` — licensing policy
- `docs/PUBLICATION_GATE.md` / [Deutsch](docs/PUBLICATION_GATE.de.md) — public-release safety and operator-decision gate
- `THIRD_PARTY.md` — external source and provenance ledger
- `SECURITY.md` / [Deutsch](SECURITY.de.md) — security reporting and sensitive-information boundary
- `CONTRIBUTING.md` / [Deutsch](CONTRIBUTING.de.md) — contribution, verification, provenance and privacy rules

### Language and implementation

- `docs/DOCUMENTATION_LANGUAGE_POLICY.md` / [Deutsch](docs/DOCUMENTATION_LANGUAGE_POLICY.de.md) — bilingual documentation convention
- `tools/` — reusable harness, context and verification utilities
- `adapters/` — consumer integration examples

</details>

## Documentation languages

Core human-facing documentation follows an **English + German** convention. Code, schemas, APIs, tests and other machine-facing artifacts stay English so bilingual presentation does not create a second technical truth or needless maintenance duplication.

See the [Documentation Language Policy](docs/DOCUMENTATION_LANGUAGE_POLICY.md).

## Status

Loop42 is a public development repository.

The **v0.1 extraction / consumer-binding foundation is verified**. Reusable context and harness mechanics, frozen CORA equivalence and the exact-revision consumer-profile contract are in place.

CORA currently pins verified Loop42 revision `de5be0fa5e085d63c8f98fe683f9936828478dbf`. That pin is intentionally exact; Loop42 `main` may continue to advance independently.

Loop42 is licensed under the MIT License.

<details>
<summary>Why 42?</summary>

Because good systems need bounded loops, honest evidence, recoverable state —  
and occasionally the right question before the right answer.

</details>
