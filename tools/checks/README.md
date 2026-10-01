# Checks

Home for generic Loop42 verification, provenance, freshness and policy checks.

Product-specific safety/test logic remains in the consumer project.

## Consumer profile validation

`consumer_profile.py` validates the project-agnostic `loop42.consumer-profile.v1` contract and can fail on a stale exact-revision pin.

```text
python tools/checks/consumer_profile.py PROFILE.json
python tools/checks/consumer_profile.py PROFILE.json --expected-revision <40-hex-commit>
```

The checker validates structure, explicit capabilities, consumer-owned product truth/Recovery, and equality between the pinned revision and the revision named by equivalence evidence. It does not perform remote Git access.


## Hygiene / entropy classification

`hygiene.py` is a pure maintenance boundary for repositories, Drive-style
workspaces and other consumer inventories. Adapters supply explicit fresh,
complete evidence; Loop42 classifies each item as `ACTIVE`, `HISTORICAL`,
`SUPERSEDED`, `MERGED_BRANCH`, `DUPLICATE_CANDIDATE`, `ORPHANED`,
`STALE_REFERENCE` or `UNKNOWN`.

The rule is **hygiene is reconciliation, not deletion**. The checker never
deletes, moves, renames or archives anything and never grants destructive
authority. A cleanup candidate still requires the consumer's action policy and
operator/retention rules. Protected items remain protected. Stale or incomplete
evidence stays `UNKNOWN`.

A matching filename is not duplicate evidence. Adapters must establish the
duplicate relationship from appropriate content/provenance evidence before
setting `duplicate_candidate=true`.

Run a strict JSON inventory through:

```text
python -m tools.checks.hygiene --input hygiene.json
```

The input schema is `loop42.hygiene-input.v1`; the deterministic report schema
is `loop42.hygiene-report.v1`.
