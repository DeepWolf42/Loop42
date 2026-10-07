# ChangeSet v1 contract

Loop42 treats model-produced code changes as proposals, not execution authority.

## Proposal operations

A `ChangeSet` contains one operation per repository-relative path:

- `MODIFY`: exact `search` / `replace` text plus the SHA-256 of the complete current file. `search` must match exactly once. Zero or multiple matches fail closed.
- `CREATE`: complete content for a path that must not already exist.
- `DELETE`: explicit delete request plus the SHA-256 of the complete current file.

Paths are bounded repository-relative POSIX paths. Parent traversal, absolute paths, backslashes and duplicate path operations are rejected.

## Verification requests are identifiers, not shell commands

A model may request bounded verification identifiers such as `unit:slicer` or `lint:python`. It does not choose an arbitrary command line. The consumer maps approved identifiers to its own tested verification actions and applies normal authority policy.

## Normalization

The pure normalizer receives an exact caller-supplied mapping of current path to text and:

1. rechecks existence and base SHA-256;
2. rejects ambiguous or stale MODIFY proposals;
3. computes the exact before/after state;
4. emits a deterministic unified diff for review/audit;
5. fingerprints the normalized result.

The normalizer performs no filesystem, Git, shell or network side effect. Before a real write, the consumer must re-read authoritative state, revalidate the proposal/permit and apply its action policy. The generated unified diff is an audit/review artifact; it is not proof that a write happened.

## Why this hybrid format

Search/replace is compact and model-friendly for existing files. Full content is unambiguous for new files. Explicit DELETE avoids implicit destructive behavior. Loop42 converts all three into one deterministic normalized changeset/diff so downstream policy, review and evidence do not depend on the provider's preferred editing syntax.
