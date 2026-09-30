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


## Bounded repository map

`repository_map.py` is a read-only navigation helper for large working trees. It
does not replace the exact source snapshot above and it is not product truth.

```text
python tools/context/repository_map.py --repo /path/to/consumer \
  --query "worker dispatch" --target tools/harness/worker_dispatch.py \
  --budget-bytes 16384
```

The map:

- considers Git-tracked files only and never edits them;
- binds selected readable entries to exact working-tree SHA-256 values plus Git HEAD;
- extracts compact top-level Python classes/functions/signatures, Markdown headings,
  and JSON top-level keys with standard-library parsers only;
- uses local Python import references plus query/explicit-target relevance for ranking;
- never silently drops an explicit target when the requested byte budget is too small;
- reports parse errors, binary/non-UTF-8 or oversized files instead of pretending they
  were understood;
- rechecks selected bytes and HEAD before returning;
- produces deterministic, fingerprinted JSON capped by the caller's byte budget.

This deliberately borrows only the **repository-map idea** from Aider: give an agent
a small navigation view before loading full files. Loop42 independently implements
a narrower standard-library version; no Aider implementation code, tree-sitter,
PageRank code or runtime dependency is imported. Exact research provenance is in
`THIRD_PARTY.md`.
