**English** · [Deutsch](LOCAL_CLIENT_PROVIDER.de.md)

# Existing local client: ChangeSet bridge

`tools.harness.local_client_provider.LocalClientChangeSetProvider` implements
the existing WorkerProvider contract for a consumer-owned local JSON client.
It uses only the standard library and existing parsers, on current main; it
does not require the older autonomous-attempt/provider-routing drafts.

```python
provider = LocalClientChangeSetProvider(trusted_transport, profile="fast64", max_tokens=1024)
result = provider.run(request)
```

The synchronous `trusted_transport(payload_bytes) -> response_bytes` invokes
the already configured client once. It must preserve the JSON string/integer
input serialization (UTF-8, compact JSON, no ASCII escaping, preserved key
order). The client returns `inputSha256` over JSON.stringify(input),
`contextSha256` over its context text, kind=model_proposal, matching profile,
mode=quick, format=json, and an answer containing strict ChangeSet v1 JSON.
Optional usage has prompt_tokens/completion_tokens. Additional envelope
metadata is ignored; unknown ChangeSet fields and duplicate JSON keys fail.

The adapter includes task ID, attempt ID, source revision, context fingerprint,
role, capabilities and untrusted source data in its context. Mismatching input
or context hashes, profile, mode, malformed output, missing capabilities or
limits fail closed. Missing propose_changes returns BLOCKED without a call.
Missing request_verification forbids verification requests in the proposal.
Transport exceptions propagate; there is no hidden retry or fallback.

The transport is trusted executable infrastructure, never model-supplied code.
It must check the actual server/process identity before sending data, enforce
timeouts and byte limits while collecting output, and own cancellation. The
adapter checks response size after collection (4 MiB); it cannot enforce an
injected callable's runtime or allocations. Input follows the existing client
limits: 8000 task UTF-16 code units (matching Node), 1 MiB task+context UTF-8, 1 MiB+16 KiB serialized
input, 8–4096 output tokens; answer is limited to 2 MiB. Wrapper instructions
consume part of the task/input budget.

Hashes identify content, not authenticity or successful work. WorkerResult.model
records the configured client profile, not an inferred weights identity. Cost
is unreported, not assumed zero. A valid result is PROPOSAL only; it cannot
write files, run commands, verify itself, or create success receipts. Consumers
still own exact source/context capture, current-state guards, action policy,
independent verification, receipt validation and reconciliation. No queue,
scheduler, model installation, Git operation or consumer pin change is added.
