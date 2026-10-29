**English** · [Deutsch](HANDOFF.de.md)

# Executable local handoff (issue #77 candidate)

One authorized host invocation reads a task, checks repository identity, exact
source and cleanliness, calls one available proposal provider, applies a bounded
ChangeSet in a detached worktree, runs registered tests, commits the verified
candidate and preserves the existing VerificationReceipt. The source checkout is
unchanged. A separate CLI process can revalidate the result without rerunning AI.

## Implementation decisions and acceptance

Use existing ChangeSet normalization, policy/permit/executor, DispatchTask and
dispatch permits, VerificationRegistry/process isolation and receipt validation.
`git_workspace.py` is reused unchanged from Loop42 draft #45 at
`25ff944816af17ca6a151a6acd6f59158adb8d09` (blob `40a47eb`); this does not adopt
its old Ollama stack or merge the draft. Draft #31 already provides optional
open-work discovery, not host dispatch; it stays separate. The new glue only owns
one explicit consumer recovery directory and one atomic task claim, no database,
daemon, scheduler or new project truth.

Plan/acceptance: real Git/process regression and failure cases first; minimal
runner; actual signed-in Codex CLI proposal on synthetic data; RED/GREEN and
candidate commit; independent status process; full tests and exact-revision CI.
Missing capability, ambiguous interruption and failed verification cannot pass.

## Once per project: trusted local profile

Keep this private operator-owned JSON outside source control. Never accept the
profile or command definitions from an issue, model or untrusted repository.

```json
{
  "repository": "example/synthetic",
  "repo": "/absolute/local/repo",
  "state_dir": "/absolute/local/recovery",
  "allowed_paths": ["answer.py"],
  "allow_commit": true,
  "allow_codex": true,
  "author_name": "Synthetic Operator",
  "author_email": "synthetic@example.invalid",
  "verifications": [{"identifier": "test:addition", "argv": ["python", "-B", "-m", "unittest", "discover"], "timeout_seconds": 30}]
}
```

`state_dir` must be outside the source repo. The origin must match the selected
GitHub repository. The checkout must be clean, including untracked files.
The selected paths must be existing regular UTF-8 files; only modifications are
supported. Registered tests are trusted programs, not a security sandbox. They
run with operator permissions; review scripts and dependencies beforehand.

## One task, one start

A capable Chat/Work/Codex host can read an approved GitHub issue through its
connected GitHub tools, reconcile open work and prepare this small local task
without asking the user to copy messages. The host owns intent/acceptance review;
the CLI does not turn arbitrary issue prose into execution authority.

```json
{
  "schema": "loop42.handoff.v1",
  "task_id": "example-issue-1",
  "repository": "example/synthetic",
  "source_revision": "EXACT_40_LOWERCASE_HEX_COMMIT",
  "task": "Correct addition in answer.py; keep its public signature.",
  "paths": ["answer.py"],
  "verification_ids": ["test:addition"],
  "require_red": true
}
```

```text
python -B -m tools.harness.handoff_cli run --input request.json --profile project.local.json
python -B -m tools.harness.handoff_cli status --input request.json --profile project.local.json
```

Set `PYTHONDONTWRITEBYTECODE=1` for verifier descendants too. The runtime requires
Python 3.12. Commands run from the Loop42 checkout. `allow_codex` explicitly
authorizes the selected task/file text and one signed-in CLI quota use. The
CLI adapter uses documented `codex exec`, an empty scratch cwd, ignores user
configuration, requests a read-only proposal, disables listed tool features and
rejects emitted non-message/non-reasoning items. This is **not** proof of zero
offered tools or a filesystem-read/privacy sandbox. Use only approved data.
No keys, extra services or installations are acquired. The provider/model must
already be callable; unavailable capability is blocked. Prompt limit is 3500
characters (also keeps each argv within the existing runner limit); executable
arguments can be visible locally. Do not use this adapter for confidential or
patient data. Monetary cost and underlying model identity remain UNKNOWN.

## Results, duplicate protection and recovery

The atomic task directory holds `claim.json` and `result.json` in the consumer's
existing recovery location. The claim binds the complete task and trusted
profile. It is never deleted automatically. The same task ID does not call the
provider twice. Reusing it with different input is rejected. Missing result after
a claim means UNKNOWN, never retry. A new attempt requires explicit reconciliation
of retained workspace, process quiescence and effects, then a new approved task ID.

DONE_VERIFIED means registered checks passed for the exact committed candidate
tree, not merge authority. Status checks task/profile, source and candidate state,
receipt fingerprint, verifier code/Python fingerprint, verifier identity/time and
all stored evidence hashes. These are trusted local records, not signatures or
proof against an attacker controlling the machine. Changed verifier/runtime or
source requires requalification. Failed verifier retains candidate and FAILED;
missing/corrupt proof is UNKNOWN. No automatic push, PR, merge or background work.

A connected host may publish a **reviewed, nonprivate summary** with task ID,
source/candidate SHAs, receipt fingerprint and checks to the existing GitHub issue
or PR through its authorized connector. Another authorized session can retrieve
that report. Local paths/raw records stay private. Remote summary is reported
evidence, not an independent local verification; CLI status needs the retained
local recovery directory. This is deliberately not automatic GitHub publication.

## Product boundaries

Official interfaces checked on 2026-10-29:
[Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)
and [Tasks and memory](https://learn.chatgpt.com/docs/dots/tasks-and-memory).
Supported connected-host task creation does not imply arbitrary cross-session
access. No direct Chat–Work–Codex session bridge or event trigger is installed
here. A host with GitHub and local execution can perform the path now; a chat
without local execution is BLOCKED_CAPABILITY for the execution step. It can
still read the shared GitHub result. A persistent unattended trigger needs a
separately verified supported host mechanism; it is not simulated by this CLI.

KI-Multistecker was inspected: its live selected-text capability is not a general
coding worker. Its current safety boundaries stay unchanged; no retired worker
is revived. Consumer configuration is generic (repo, paths, verifier IDs).
CORA/dentalCOM/Arthur retain their own state, pins and safety/privacy rules.

## Measured scope

The live synthetic fixture and exact measured results belong in the candidate PR
receipt, not this reusable contract. Tests using deterministic providers are
labeled test doubles. User copy/paste before this work was not instrumented:
UNKNOWN. The live host path needs one start and zero user intermediate transfers;
it does not prove every ChatGPT surface exposes that host. Total session tokens,
host actions and monetary cost are UNKNOWN unless separately captured.
