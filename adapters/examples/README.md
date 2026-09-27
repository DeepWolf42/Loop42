# Adapter examples

Examples demonstrate how a consumer project can bind to Loop42 without moving its product truth into this repository.

## Consumer profile shape

A consumer profile is intentionally small. Example:

```json
{
  "schema": "loop42.consumer-profile.v1",
  "loop42": {
    "repository": "Example/Loop42",
    "revision": "1111111111111111111111111111111111111111"
  },
  "consumer": {
    "name": "Example",
    "repository": "Example/Project",
    "context_manifest": "project-context.json",
    "canonical_sources": {
      "project_state": "docs/CURRENT_PROJECT_STATE.md",
      "recovery": "docs/CURRENT_PROJECT_STATE.md"
    }
  },
  "capabilities": [
    "context.snapshot",
    "context.checkpoint",
    "harness.ollama.proposal"
  ],
  "authority": {
    "product_truth": "consumer",
    "recovery": "consumer",
    "execution": "consumer-policy"
  },
  "evidence": {
    "equivalence_suite": "example-equivalence-v1",
    "status": "verified",
    "verified_loop42_revision": "1111111111111111111111111111111111111111"
  }
}
```

The repeated `1` revision is a placeholder for documentation only. A real consumer must pin an exact verified Loop42 commit and provide matching equivalence evidence.

CORA is the first real consumer and remains the owner of its product truth.
