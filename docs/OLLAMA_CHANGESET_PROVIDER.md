# Ollama ChangeSet provider

`ollama_changeset_provider.py` is the first adapter that implements Loop42's provider-neutral `WorkerProvider` contract for code proposals.

It deliberately starts with local Ollama because this path adds no second AI subscription or metered API requirement. The adapter is still only a proposal source: it never receives filesystem, shell, Git, merge, publish or physical authority.

## Boundary

The adapter:

1. accepts one bounded `WorkerRequest`;
2. requires the explicit `propose_changes` capability;
3. checks local Ollama model inventory and refuses implicit model download;
4. calls only the configured loopback Ollama origin;
5. requests a strict structured proposal envelope containing rationale, evidence and `ChangeSet v1`;
6. parses and validates the returned JSON again locally;
7. rejects requested verification IDs unless the request also grants `request_verification`;
8. returns a provider-neutral `WorkerResult` with exact task/attempt/source/context identity and token usage when reported.

The adapter performs no automatic retry or provider fallback. A retry or model switch is a new visible Loop42 attempt so dispatch/reconcile truth cannot be hidden inside a provider library.

## Why Ollama first

This is an integration proof, not a declaration that one local model is the permanent primary worker. If the same contract works end to end with Ollama, OpenAI, Anthropic, Gemini, DeepSeek or another provider can later be added behind a thin adapter without changing ChangeSet, policy, verification or recovery semantics.

Provider selection and economics remain orchestration concerns. A local worker can handle cheap/routine proposal work; stronger paid workers can be introduced only where measured task success justifies the added cost.

## Still not execution authority

A valid Ollama `WorkerResult` must still pass the normal Loop42 path:

`WorkerResult -> ChangeSet normalization -> action policy -> fresh permit -> workspace apply -> registered verification -> reconcile/retry/recovery`

Only the consumer/runtime performs those later steps.
