**English** · [Deutsch](CANDIDATE_EVIDENCE_CONTRACT.de.md)

# Evidence-Bound Candidate Evaluation Contract

Status: generic method contract; no runtime or consumer adoption is implied

## Purpose

Some consumers must choose among several technically viable routes while preserving evidence, hard constraints and uncertainty. Loop42 may support that pattern without owning domain semantics.

The generic question is:

> Given a finite set of consumer-defined candidates, which candidates are ruled out by hard constraints, which remain UNKNOWN, and which non-dominated candidates remain for a consumer-owned decision?

This contract is intentionally domain-neutral.

## Existing contracts remain authoritative

This contract extends the existing Matrixloop, `/truth`, `/gaps`, action-policy and consumer-profile boundaries. It does not create another loop, state store, authority layer or product truth.

Consumer repositories continue to own their requirements, policies, domain models, weights/objectives, safety meaning and final recommendation semantics.

## Generic concepts

### Evidence-bound claim

A decision-relevant claim should retain enough context to determine whether it is applicable now:

- source/reference identity;
- source revision, artifact hash or other stable identity when available;
- scope/context/conditions;
- freshness or dependency state;
- explicit assumptions and limitations;
- consumer-compatible validity/evidence status.

Loop42 must not require a universal numeric confidence score. Freshness, provenance, applicability, uncertainty and validity are different dimensions and must not be silently collapsed.

### Capability assertion

A capability assertion states that a subject can provide a consumer-defined capability under explicit conditions and with explicit evidence.

Conceptually:

```text
subject
+ capability identifier
+ conditions
+ evidence references
+ applicability/freshness
+ status
```

The capability identifier and its physical or business meaning belong to the consumer.

A label, product name, model family or provider name is not by itself evidence that a capability is available.

### Candidate

A candidate is an opaque consumer-defined option with deterministic identity. Loop42 does not prescribe its internal domain fields.

The consumer may enumerate candidates itself or through an authorized deterministic producer. Candidate generation is separate from candidate evaluation.

### Constraint result

A consumer-defined constraint evaluation should resolve to a small explicit state such as:

- PASS — applicable evidence supports satisfaction;
- FAIL — applicable evidence establishes violation;
- UNKNOWN — evidence is missing, stale, conflicting, inapplicable or insufficient.

A hard constraint that resolves UNKNOWN must not be converted into PASS by a ranking score.

The consumer defines which constraints are hard and which are negotiable.

## Generic evaluation order

A reusable Loop42-compatible evaluation should preserve this sequence:

1. reconcile authoritative inputs and exact revisions;
2. establish deterministic candidate identities;
3. evaluate hard constraints and preserve PASS / FAIL / UNKNOWN with evidence references;
4. remove only candidates that are actually ruled out;
5. stop or request resolution when a decision-critical UNKNOWN blocks safe/useful comparison;
6. compute consumer-defined objective values only for sufficiently evidenced viable candidates;
7. remove candidates that are dominated across the declared objectives when the consumer requests Pareto-style reduction;
8. return the remaining decision set with reasons, evidence and unresolved limits;
9. leave the final domain recommendation and any side effect to consumer policy/authority.

A consumer may deliberately choose a non-Pareto decision rule. Loop42 must not force one universal optimizer.

## Reproducibility

A candidate assessment should be reproducible from its declared basis.

Where useful, consumers may fingerprint:

- candidate identity;
- requirement/constraint set;
- capability/evidence inputs;
- objective definitions;
- evaluator version/configuration.

A repeated assessment on the same declared basis should not silently change because an unrelated source changed elsewhere.

If relevant dependencies change, prior results are STALE or require reassessment according to the consumer's existing evidence semantics.

## Robustness and operating envelopes

Loop42 may transport a generic distinction between:

- a claimed/observed maximum; and
- a consumer-defined reliable operating envelope under stated conditions.

Loop42 does not determine the engineering margin. The consumer owns how reserve, noise factors and robustness are calculated and what evidence is sufficient.

## Provenance is not a trust ladder

Source classes may be recorded, but generic Loop42 must not assume that one class is always more trustworthy than another.

For example, a local test can be highly applicable but badly designed; a vendor result can be well controlled but poorly applicable. The consumer evaluates fitness of evidence to the actual claim.

Conflicting applicable evidence remains visible until resolved by consumer rules or direct verification.

## Authority boundary

This contract does not authorize Loop42 to:

- invent domain requirements;
- select consumer safety limits;
- assign hidden preference weights;
- turn model agreement into evidence;
- convert UNKNOWN into PASS;
- choose or execute real-world actions;
- advance a consumer's exact Loop42 pin.

Model output can propose candidates or interpretations only where the consumer already permits that role. It remains proposal material until independently checked under the consumer contract.

## Example consumer mapping

An FDM consumer could map:

```text
candidate = material + machine + build orientation + process envelope
hard constraints = service temperature, geometry, machine envelope, required evidence
objectives = robustness, time, cost, mass, surface or other declared goals
```

Loop42 knows none of the FDM meaning. It only preserves the generic evaluation/evidence mechanics.

## Adoption rule

A consumer adopts this contract only through its existing exact-revision binding and equivalence/verification process.

Merging this document into Loop42 does not prove a runtime implementation, does not change any consumer profile, and does not create an automatic decision engine.
