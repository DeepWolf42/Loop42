# ChangeSet execution and verification

`ChangeSet v1` is still only a proposal until a consumer explicitly turns a normalized change into bounded workspace side effects.

## Permit before write

`changeset_executor.py` uses the same fail-closed pattern as worker dispatch:

1. read the exact workspace state for every proposed path;
2. require the normalized before-hash (or required absence for CREATE);
3. evaluate Loop42 action policy for each `changeset.modify`, `changeset.create` or `changeset.delete` request;
4. issue a short-lived permit bound to the ChangeSet fingerprint, observed basis and policy decisions;
5. immediately before applying, re-read state and policy and reject a stale permit.

Headless writes are denied by the existing action-policy default. A consumer that wants autonomous edits must explicitly allow the bounded repository target/mode it controls.

The executor refuses symlink targets/path components and non-UTF-8/non-regular existing files. Desired file content is staged before repository writes. Existing files are moved to temporary rollback backups during the operation; ordinary process-visible failures trigger best-effort rollback. A hard process/host interruption is still UNKNOWN until the existing side-effect reconciliation machinery observes the target state; the executor does not pretend that rollback always happened.

The executor does not commit, push, merge or publish.

## Verification IDs, not model commands

`verification_registry.py` resolves the model's requested verification IDs against a consumer-owned registry. Every requested ID must resolve before the first process starts.

Registry entries contain fixed argv values and timeouts. They run with `shell=False` in the explicit workspace, with stdin disabled and bounded captured output. Unknown IDs fail closed. By default a failed/timeout verification stops later checks.

This keeps the authority split explicit:

- model: request `unit:cora-slicer`;
- consumer configuration: map that ID to the approved argv;
- Loop42: run it and record the actual exit/result;
- model output never becomes an arbitrary terminal command.

Passing verification is evidence about the modified workspace. It is not merge/release authority.
