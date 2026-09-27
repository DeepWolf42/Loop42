# Consumer Profile Contract

A consumer profile binds one project to one exact Loop42 commit while the consumer keeps its own product state and Recovery.

Schema: `loop42.consumer-profile.v1`.

Required fields:
- `loop42.repository`
- `loop42.revision` as an exact 40-hex Git commit
- `consumer.name`
- `consumer.repository`
- `consumer.context_manifest`
- `consumer.canonical_sources.project_state`
- `consumer.canonical_sources.recovery`
- explicit `capabilities`
- `authority.product_truth = consumer`
- `authority.recovery = consumer`
- `authority.execution = consumer-policy`
- `evidence.equivalence_suite`
- `evidence.status = verified`
- `evidence.verified_loop42_revision`, equal to the pinned revision

Branches are not valid pins. Missing or stale expected revisions fail validation visibly.

Use `tools/checks/consumer_profile.py PROFILE.json --expected-revision <commit>` for structural and pin validation.

Validation does not prove remote commit existence. Repository access and checkout verification remain harness responsibilities.

A valid profile never authorizes automatic cleanup. Frozen equivalence must pass first; predecessor deletion is always a separate explicit decision.
