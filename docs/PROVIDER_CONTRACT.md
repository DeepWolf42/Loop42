# Worker provider contract

Loop42 is model- and vendor-neutral. OpenAI/Codex, Anthropic/Claude, Google/Gemini, DeepSeek, Ollama and future providers belong behind thin adapters.

The generic core exchanges only `WorkerRequest` and `WorkerResult` values. A successful worker result may contain a `ChangeSet v1` proposal; it never grants filesystem, shell, Git, merge, publish or physical authority.

## Request identity

Every request is bound to task ID, attempt ID, source revision and context fingerprint. It also carries a bounded task/context payload, requested role and explicit capability identifiers.

Capabilities describe what the worker may propose or request. They do not grant the provider a direct tool handle.

## Result identity and accounting

Every result repeats the exact request identity and records provider/model identity, a short rationale summary, bounded evidence references, optional usage/cost accounting and an optional raw-response fingerprint.

`PROPOSAL` requires a `ChangeSet`. `BLOCKED` and `FAILED` must not carry code changes.

The contract deliberately does not require hidden chain-of-thought or a numeric confidence score. Loop42 trusts independently verified evidence, state identity, policy decisions and tests instead.

## Provider economics

The core does not require any paid provider. A deployment may use only local adapters, one subscription-backed interactive agent, metered APIs, or a mixture. Provider selection, cost ceilings and escalation are policy/configuration concerns; they must not change the generic task/change/reconcile semantics.

A later adapter may report usage/cost so routing can optimize for the lowest sufficient execution tier. Automatic provider fallback/retry must remain visible to Loop42 as distinct attempts rather than being hidden inside an adapter.
