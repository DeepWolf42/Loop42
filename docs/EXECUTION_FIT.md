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
