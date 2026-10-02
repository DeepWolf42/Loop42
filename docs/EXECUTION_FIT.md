# Execution Fit

Status: active generic Matrixloop rule

Execution Fit prevents a technically correct plan from becoming unnecessary operator work. It is checked during **TARGET** and **PRE-MORTEM**, before detailed setup or UI instructions.

## Decision order

### 1. Capability Fit

Verify the route is actually available in the current environment.

Check material prerequisites such as:

- tool or connector capability;
- repository/account visibility and plan entitlement;
- permissions and policy restrictions;
- operating system and software version;
- hardware and network availability;
- required credentials or external services;
- cost-bearing or irreversible prerequisites.

Do not infer availability from a UI control merely existing. If a feature is only advisory, unavailable on the current plan or blocked by permissions, treat that as a failed prerequisite.

### 2. Value Fit

Ask whether the route is worth doing for the real goal.

Compare:

- expected useful delta;
- financial cost;
- setup and maintenance complexity;
- safety and reliability impact;
- future lock-in or migration cost;
- whether a simpler path already meets the requirement;
- whether a different or new tool creates enough net benefit to justify switching, learning, maintenance, lock-in and operator cost.

A paid upgrade, new dependency or more elaborate architecture needs proportional value. Do not preserve a route just because work on it has already started.

### 3. Operator Fit

Among viable routes, choose the lowest-friction path that still satisfies the goal and safety/quality constraints.

Prefer:

- one actionable block over many fragmented commands;
- existing tools when they remain the best overall fit;
- a new tool when its demonstrated net benefit clearly outweighs migration, learning, maintenance, lock-in and operator cost;
- reversible changes over invasive setup;
- automatic verification over asking the operator to inspect values manually;
- direct evidence over screenshot chains;
- defaults that match the actual environment over generic instructions.

Avoid:

- unnecessary copy/paste;
- repeated questions already answered by context or tools;
- UI navigation before prerequisites are known;
- setup steps that cannot become effective;
- asking the operator to perform checks that the available tools can verify directly.

## Operator sovereignty

Reducing operator effort must never silently reduce operator authority.

Automation may proceed without interruption only inside already-authorized, bounded and reversible work. The operator keeps the final decision for protected actions such as:

- spending money or enabling paid services;
- publishing, releasing, merging into a protected product state, or changing repository visibility;
- real machine motion, heating, actuation or other physical-world actions;
- changing safety, quality or authority boundaries;
- destructive or materially irreversible changes;
- major product-direction decisions that exceed the currently authorized goal.

Decision compression should reduce how often the operator is interrupted, not transfer these decisions away from them. When a protected decision is required, present the smallest decision that preserves meaningful choice.

## Task and automation compression

Task capacity and operator attention are finite resources.

Before creating another agent, scheduled task, specialist role or monitoring loop:

1. check whether the work can be completed in the current run;
2. check whether it can be folded into an existing task without obscuring responsibility;
3. check whether a local worker can do the bounded preparation instead of consuming another scarce orchestration slot;
4. create a new persistent task only when separation has clear value.

Prefer one coherent task with several related sources over several overlapping watchers. Preserve spare capacity for unexpected or high-value work.

## Resource and client fit

Execution capacity and client availability are explicit prerequisites.

Before escalating or decomposing a task, compare the total execution cost of viable paths. Count scarce model/agent quota, tool calls, repeated context loading, operator effort, latency, failure/recovery risk and verification quality together. Prefer direct reasoning or a narrow tool call when sufficient, but do not force a chat-first sequence when one specialist or long-running agent can finish the bounded task with lower total cost and equal or better verification. Group compatible work when that avoids repeated context loading, but keep verification and ownership clear.

Treat plan-bounded quotas, rate limits, model/agent usage, task slots and context as finite resources. Do not spend scarce capacity on repeated full reconciliations, duplicate checks, polling that can be event-driven, or re-reading evidence that is still fresh enough for the decision. Preserve reserve capacity for failures, high-value implementation and recovery.

Also verify the active client or host. Browser, desktop, mobile and automated runtimes can expose different capabilities even under the same account. If the selected action is unavailable on the current client, do not loop on failed attempts or provide long unusable click-paths. Prepare the bounded work, switch/defer to a capable client when practical, or choose a lower-friction fallback that preserves the goal.

## Tool routing and client handoff

Choose tools by task shape and total execution cost, not by a fixed escalation ladder. Tiers may be skipped when a specialist path is clearly cheaper or more reliable.

- Use direct reasoning when no fresh external state, file mutation or specialized execution is required.
- Use a narrow connector/tool call when one authoritative source or bounded action is enough.
- Use a specialist tool when domain-specific capability materially improves correctness, fidelity or operator effort, for example design tools for editable UI work.
- Use a coding/repository agent when implementation, repository inspection, tests or patch iteration dominate the task.
- Use long-running or cross-app execution when the goal spans several systems/steps and would otherwise require repeated context reconstruction or manual orchestration.
- Do not invoke several overlapping tools merely to increase confidence; add another tool only when it contributes distinct evidence or execution value.

If the selected path is unavailable on the current client, produce a bounded handoff instead of restarting the task from scratch. Reuse the existing work record/chat; do not create a second state store. The handoff should contain only what the receiving client needs: goal, authoritative live basis/revisions, completed preparation, selected tool/path, remaining action, acceptance/stop condition, and any protected approval still required.

On resume, re-check only mutable dependencies and live heads that could invalidate the handoff. Stable preparation and unaffected evidence should be reused rather than re-derived.

## Failure behavior

If Capability Fit fails:

1. stop the blocked route before downstream setup;
2. state the missing prerequisite or limitation;
3. look for a simpler viable fallback;
4. evaluate whether paying, upgrading or adding complexity has enough value;
5. give operator instructions only for the selected actionable route.

If Value Fit fails, discard or park the route.

If Operator Fit fails, simplify the execution path before handing it to the operator.

## Evidence

Execution Fit claims should use current evidence appropriate to the decision: live account/repository state, tool capability responses, exact hardware/software state, current documentation or a directly reproduced limitation.

A plausible assumption is not enough when it would cause operator work, cost or an architectural commitment.

## Frozen regression scenario

`tests/frozen_scenarios/execution_fit_private_repo_paid_feature_v1.json` captures the failure mode that motivated this rule:

- a private repository exposes a branch-ruleset UI;
- enforcement requires a paid entitlement;
- the bad path gives detailed ruleset setup instructions before checking entitlement;
- the expected path verifies the prerequisite first, evaluates upgrade value, rejects unnecessary complexity, offers the simplest viable fallback and only then gives actionable steps.

The scenario is generic. GitHub is only the concrete fixture used to keep the operator-friction failure reproducible.
