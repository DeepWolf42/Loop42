**English** · [Deutsch](VERIFICATION_RECEIPT_RECOVERY.de.md)

# Recovering saved verification receipts

Both Dispatch and receipt recovery restrict `--input` paths to regular files
of at most1MiB. Final symlinks, directories, devices and FIFO descriptors are
rejected. Type and size are checked on the opened descriptor before reading;
the byte cap is checked again afterwards. POSIX uses O_NONBLOCK/O_NOFOLLOW where
available; Windows uses binary mode explicitly. The Windows symlink precheck is
not atomic, and parent-directory symlinks may still be followed. This is not a
filesystem sandbox, authentication or a general IO deadline. `--input -` retains
the explicit stdin stream boundary and its caller-owned EOF contract, without
adding a new timeout.

`parse_receipt(bytes)` restores the existing VerificationReceipt data contract
from strict UTF-8 JSON: exact fields/schema, no duplicate keys/non-standard
constants, timezone-aware timestamp, at most 1 MiB, 128 criteria and 64 evidence
references per criterion. Parsing preserves claims; it does not verify them.

The separate JSON boundary runs as:

```text
python -m tools.harness.verification_receipt_cli --input request.json
```

Request fields (all required, no extras):

- schema: `loop42.verification-receipt-cli.v1`;
- receipt: saved `loop42.verification-receipt.v1` object;
- task: current DispatchTask object with task_id, attempt_id, source_revision,
  context_fingerprint and ordered acceptance_criteria;
- subject_fingerprint: independently re-read current subject SHA-256;
- verifier_id and verifier_revision: current trusted verifier basis;
- observed_at: timezone-aware current observation;
- evidence_fingerprints: exact source-to-SHA-256 object for independently
  re-read evidence referenced in the receipt.

The result contains schema and one serialized AttemptArtifact only when the
receipt matches the full task identity, exact ordered criteria, subject,
verifier and all evidence digests. All criteria must PASS with evidence. A
receipt dated after the observation is rejected. Invalid input exits 2 without
a stdout artifact. Input may also come from stdin; total request limit is 1 MiB.
The artifact can feed the existing worker-dispatch JSON boundary unchanged.

This is a validation tool, not a scheduler or a new state store. It reads only
the supplied request and prints a decision: no model, queue writes, subprocess
commands, GitHub updates or automatic retries. Consumers must freshly obtain
and authenticate the inputs, enforce live revision/precondition checks and
preserve their own authority and stop rules. Self-supplied matching hashes do
not establish trustworthy execution, environment freshness or physical truth.
The CLI does not enforce a universal maximum receipt age: freshness depends on
the consumer's complete dependencies, trusted verifier and current observations.

After an interrupted result publication, independently re-read the destination.
An exact owned receipt marker can confirm an already delivered result; a
conflicting marker must stop. Absence of a marker after an ambiguous write is
not permission to rerun a model or blindly repeat a publication. Existing
side-effect reconciliation and consumer write policy remain authoritative.
