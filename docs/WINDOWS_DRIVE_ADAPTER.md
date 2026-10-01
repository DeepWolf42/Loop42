# Windows / Drive folder adapter

Status: proposed Loop42 consumer adapter contract  
Canonical implementation: `tools/harness/drive_folder_adapter.py`

## Purpose

This adapter bridges a local filesystem folder that is synchronized by Google Drive
(or an equivalent folder-sync provider) into Loop42's generic worker-dispatch
contract.

It does **not** start Ollama, a worker process, Drive sync, or any consumer action.
Its job is to translate provider evidence into exact Loop42 task/attempt identity,
fail closed on incomplete/legacy evidence, and protect a local queue write with the
existing `DispatchPermit` time-of-check/time-of-use guard.

## Expected provider surfaces

The configured root must contain all of these directories:

- `00_Inbox`
- `10_Results`
- `90_Logs`
- `95_Error`
- `99_Archive`

A missing surface blocks dispatch. The adapter never treats a missing result/error
directory as proof that no terminal evidence exists.

## Fresh host/session evidence

`90_Logs/loop42-host-state.json` uses schema
`loop42.drive-host-state.v1`.

Required fields:

- `observed_at` with timezone offset;
- `session_id`;
- `reachable`.

Optional fields:

- `safety_stop`;
- `worker_sessions[]` with session/task/attempt/progress identity.

A missing host file becomes UNKNOWN through the canonical reconciler. A stale file,
changed host session, safety stop, or busy worker invalidates a previous permit.

## Modern task manifest

A new queue item uses `loop42.drive-task.v1` and contains:

- task ID;
- attempt ID;
- exact source revision;
- context fingerprint;
- ordered acceptance criteria;
- explicit observed timestamp.

The adapter writes new tasks as
`<task_id>__<attempt_id>.task.json` only after revalidating a previously issued
permit against a fresh provider rescan.

The write is atomic on the local filesystem (`fsync` + replace), but that does
**not** prove that cloud sync completed. The adapter reports
`cloud_sync_confirmed: false`; cloud/provider arrival must be observed separately.

## Terminal artifacts

Modern provider artifacts use `loop42.drive-artifact.v1`.

Surfaces are strict:

- `10_Results/*.result.json` must contain `kind: result`;
- `95_Error/*.error.json` must contain `kind: error`;
- `99_Archive/*.archive.json` must contain `kind: archived`.

A result requires a receipt fingerprint even before the stronger verification
receipt contract is merged into the generic core. Wrong schemas, duplicate JSON
keys, wrong surface/kind pairs, malformed timestamps, or invalid identity are
provider-evidence errors and block dispatch.

## Legacy evidence

Existing `.md` and `.txt` files remain visible as legacy provider evidence but
are **not** converted into modern identity.

`legacy-reconcile` therefore returns UNKNOWN and:

- never calls a historical START line proof of RUNNING;
- never calls missing terminal evidence proof of FAILED;
- never grants retry;
- never grants replacement dispatch;
- requires conscious operator reconciliation.

This keeps old queues recoverable without fabricating task/attempt/source/context
identity that they never recorded.

## Commands

Inspect provider evidence without side effects:

```text
python -m tools.harness.drive_folder_adapter --root "G:\...\DeepThought_Away" snapshot
```

Classify one legacy job:

```text
python -m tools.harness.drive_folder_adapter --root "G:\...\DeepThought_Away" \
  legacy-reconcile --name "legacy_job.md"
```

Reconcile a modern task:

```text
python -m tools.harness.drive_folder_adapter --root "G:\...\DeepThought_Away" \
  reconcile --task next.task.json
```

Issue a permit from fresh idle evidence:

```text
python -m tools.harness.drive_folder_adapter --root "G:\...\DeepThought_Away" \
  issue-permit --task next.task.json
```

Before the actual queue write, persist the returned permit as JSON and revalidate it
through `validate-permit` or use `enqueue`, which performs the fresh rescan and
permit validation immediately before the atomic local write.

## Authority boundary

The adapter is not approval authority. A valid permit only proves that the provider
basis still matches the previously reconciled dispatch basis. Consumer action policy,
operator approval where required, Drive/cloud-sync confirmation, worker execution,
model output, verification, merge/release and physical actions remain outside this
adapter.

## Current verification scope

The repository tests simulate the Drive folder structure with temporary directories.
They cover legacy UNKNOWN behavior, missing-surface blocking, invalid provider JSON,
permit invalidation after host/safety changes, atomic queue writing and modern result
reconciliation.

A passing repository test is **not** proof that the actual Windows Google Drive client
or DeepThought worker has completed an end-to-end roundtrip. That live E2E remains a
separate consumer gate.
