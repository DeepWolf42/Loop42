# Context tools

Reusable context assembly, source identity, stale-state and guarded checkpoint helpers.

Consumer-specific manifests and product state remain in the consumer repository. Loop42 provides the mechanism, not a second product truth.

## Generic context manifest

A consumer can place a small manifest such as `loop42-context.json` at its checkout root:

```json
{
  "schema": "loop42.context-manifest.v1",
  "roles": {
    "project_state": "docs/CURRENT_PROJECT_STATE.md",
    "architecture": "docs/ARCHITECTURE.md",
    "open_tasks": "docs/CURRENT_PROJECT_STATE.md"
  },
  "external_sources": []
}
```

Only `project_state` is mandatory. Additional role names are consumer-defined. Repeated paths are deduplicated in the snapshot.

## Commands

```text
python tools/context/project_context.py --repo /path/to/consumer read
python tools/context/project_context.py --repo /path/to/consumer checkpoint --result reviewed-result.json
```

The tool:

- binds a snapshot to exact local source bytes, manifest hash and Git HEAD;
- refuses missing, oversized, escaping or symlinked sources;
- reports remote freshness as `UNKNOWN` rather than inventing it;
- re-reads the basis before returning or replacing state;
- serializes cooperating checkpoint writers through the Git common directory;
- writes only the consumer-declared `project_state` file;
- never commits or pushes.

A checkpoint is mechanical writeback of an already-reviewed result. Its text is not automatically promoted to verified fact.

## Extraction provenance

The generic implementation was extracted from the proven CORA standard-library context helper, using `DeepWolf42/C.O.R.A.` revision `665bdd49724f27258ca4633b0dc5fa8fbb9ae602` as the extraction basis. CORA-specific schema names, product paths, lock names and authority language were removed or generalized. CORA remains the owner of its product state and consumer-specific manifest.
