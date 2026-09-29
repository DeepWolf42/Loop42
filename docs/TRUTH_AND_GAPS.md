**English** · [Deutsch](TRUTH_AND_GAPS.de.md)

# /truth and /gaps

Status: agent workflow contract; no executable slash-command router is implemented.

These commands expose existing Matrixloop checks. They do not introduce another loop, state store, authority or permission. Their scope is the current agreed target. Commands are case-insensitive at the conversational interface (`/Truth` means `/truth`); an agent must not imply that a host supports native dispatch.

## /truth — assess the evidence

1. Resolve authoritative sources and exact live revisions, including the consumer's pinned Loop42 revision. Record the checked scope, time and unavailable sources.
2. Compare decision-relevant claims with direct source, code and verification evidence. A document saying "complete" is a claim, not proof of behavior.
3. For each claim, report its evidence reference, applicable revision/context, limitation and status:
   - CONFIRMED: direct applicable evidence supports this precise claim.
   - ASSUMED: an explicit working assumption, not established fact.
   - UNVERIFIED: evidence is missing, inaccessible or insufficient.
   - CONTRADICTED: applicable evidence refutes the claim; show the counterexample.
   - CONFLICT: applicable sources disagree and precedence does not resolve them.
   - STALE: previously relevant evidence has changed dependencies or an incompatible basis.
4. State the consequence for the current target and the smallest useful verification.

These are report labels, not replacements for a consumer's evidence types. Absence of evidence is not falsity. Hashes establish identity, not physical truth. CI proves only its executed checks on its recorded revision; synthetic tests do not establish physical performance. Agreement between model answers is not independent evidence.

Track freshness separately from support: stale evidence cannot confirm the current claim. A newer timestamp alone cannot resolve a conflict. Reuse unaffected evidence only with an explicit dependency/scope justification.

## /gaps — compare evidence with the agreed goal

Use the current /truth assessment and explicit acceptance criteria. If the goal is unclear, identify that uncertainty before declaring completeness.

For each material gap report: unmet criterion, supporting evidence or uncertainty, consequence, dependency/blocker, smallest next action and closure evidence. Distinguish:
- a missing implementation or reproduced defect;
- missing verification or unavailable evidence;
- an external prerequisite;
- a decision requiring the operator's authority.

Prioritize safety/correctness blockers, then prerequisites and the smallest useful deliverable. Improvements outside the accepted goal are optional proposals, not blockers. Deduplicate against existing issues, branches and verified completed work. Do not reopen completed work without changed dependencies or a concrete counterexample.

Default output: a short evidence verdict, up to three highest-impact gaps, one recommended next action, and explicit coverage limits. "No gaps found in the checked scope" is not a claim of global completeness. If required evidence is unavailable, record the blocker and stop that dependent work; other already-authorized independent work may continue.

## Integration with Matrixloop

- RECONCILE: /truth resolves the current basis.
- TARGET: /gaps selects one useful bounded delta.
- VERIFY and FRICTION: update affected claims using results and counterexamples.
- VALUE CHECK: /gaps compares the result with acceptance criteria.
- STOP / ITERATE: existing stop rules and budgets apply.

Do not add mandatory full-repository audits at each stage. Reuse a current assessment and recheck only affected claims, dependencies or previously unavailable evidence. A standalone command inspects and reports; it does not authorize writes or execution. An ongoing authorized work run may act on findings within its existing bounds.

Persist only reviewed, useful deltas through existing checkpoint/recovery mechanisms. Recheck live HEAD before every persistent write. Keep product findings in the consumer's existing authority; keep generic method definitions here. Never silently advance an exact consumer pin.

## Review scenarios

These are contract acceptance examples, not executed software tests.

| Situation | Required result |
|---|---|
| "Ready" in docs, no behavioral evidence | Claim UNVERIFIED; request the missing check |
| Passing tests on revision A, relevant code changed at B | Evidence STALE for that claim at B |
| Unrelated documentation change | Reuse evidence only after checking relevant dependencies |
| Missing network access | Source unavailable; no invented pass or failure |
| Green synthetic printer fixture | Software check confirmed; physical usefulness UNVERIFIED |
| Two applicable sources disagree | CONFLICT until precedence or direct evidence resolves it |
| Missing hardware commissioning | External prerequisite, not an invitation to fabricate measurements |
| Optional feature outside acceptance criteria | Optional proposal, not a completion blocker |
| All scoped criteria supported | No remaining gap in checked scope; stop |
| Consumer pins an older Loop42 revision | Report the pin; do not claim automatic adoption |

## Adoption boundary

Merging this contract into Loop42 does not change consumer pins, host capabilities or automations. Consumers adopt a new revision only through their existing verification/binding process. Until then, a directly requested conversational assessment may use this method without claiming that the pinned runtime implements it.
