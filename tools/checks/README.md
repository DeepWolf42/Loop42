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
