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

The Windows evidence writer `tools/harness/windows_drive_host_state.ps1` can
produce this file without starting a worker or model. It derives a stable host
session from the Windows boot time, carries the existing safety flags, and reports
`unidentified_worker_count` when a DeepThought worker process exists without
modern task/attempt identity. Any such unidentified worker blocks dispatch.

The existing DeepThought watchdog already has a 15-second supervision loop, so the
intended deployment is to invoke this one-shot evidence writer from that existing
loop rather than creating another scheduler or supervisor.

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

## Unverified worker proposals

A worker/model response is not a terminal result. Modern workers may therefore
write a proposal manifest using `loop42.drive-proposal.v1` plus a sibling content
file in `10_Results`.

The proposal manifest binds task/attempt/source/context identity, worker session,
prompt-contract SHA-256, model identifier, content filename and content SHA-256.
The adapter verifies the sibling content hash before accepting the proposal as
provider evidence.

A proposal never becomes `TaskLifecycle.SUCCEEDED` by itself and blocks replacement
dispatch as `unverified_proposal_requires_verification` until matching terminal
RESULT/ERROR evidence exists. This preserves the boundary "model output is a claim,
not verified completion."

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
are **not** converted into modern identity. Historical legacy files already in
Results/Error/Archive are retained diagnostics and do not permanently block new
work. An unresolved legacy job still present in Inbox does block replacement
dispatch until consciously reconciled.

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


## Minimal worker integration hook

`tools/harness/windows_worker_contract.psm1` is the intended shim for the existing
PowerShell worker. It deliberately has no model transport, process-start, queue-write,
RESULT or receipt authority.

The later local worker patch is reduced to four identity calls around its existing
logic:

1. after accepting a modern task manifest, call `Start-Loop42WorkerSession`;
2. while work is genuinely progressing, call `Update-Loop42WorkerProgress`;
3. after writing the raw response content into `10_Results`, call
   `Write-Loop42ProposalManifest` with the exact prompt-contract fingerprint and
   model identifier;
4. in a `finally` boundary, call `Clear-Loop42WorkerSession`.

The proposal helper hashes the already-written response file and emits only
`loop42.drive-proposal.v1`. It cannot create terminal RESULT evidence and cannot
invent a receipt. This keeps the worker's authority at "produced an unverified
proposal" even when the model call itself succeeds.

The shim also owns session identity fail-closed: a second `begin` refuses to
overwrite an existing session file, progress/clear refuse another process's
session, and proposal emission derives its worker-session ID from the current
same-process session rather than accepting one from the caller. A task/session
mismatch therefore blocks proposal publication instead of being papered over.

## No-model identity roundtrip

`tests/frozen_scenarios/drive_identity_roundtrip_without_model_v1.json` exercises
the complete provider identity/reconciliation lifecycle without an AI model:

1. fresh idle host -> permit;
2. permit-revalidated atomic local queue write;
3. identified worker session -> RUNNING;
4. identity-bound proposal -> still unverified and dispatch-blocking;
5. receipt-bound result while worker still owns the attempt -> SUCCEEDED but not
   dispatchable;
6. fresh idle worker evidence -> SUCCEEDED and dispatchable;
7. a new attempt can receive a new permit.

This proves the Loop42 provider/control-plane path only. It intentionally does not
claim real Google Drive synchronization, real Windows worker integration, or a model
response.
