# Provider routing policy

Loop42 routes by **role, capability, availability and incremental cost**, not by hard-coded vendor names.

A provider/model is configuration behind a `ProviderProfile`. Profiles declare:

- roles they can serve, for example `execution` or `recovery`;
- capabilities they can satisfy;
- an incremental cost tier;
- an operator/benchmark preference rank inside that tier;
- optionally a conservative per-attempt cost estimate.

Only freshly `AVAILABLE` candidates are eligible. UNKNOWN availability fails closed.

## Cost order

The generic cost tiers are:

1. `ZERO_OR_INCLUDED` — local compute or a callable harness whose use is genuinely covered already;
2. `LOW_METERED`;
3. `STANDARD_METERED`;
4. `PREMIUM_METERED`.

Loop42 chooses the **lowest sufficient tier first**. A cheaper worker that lacks the requested role or capability is not "sufficient" and is skipped.

The core does not label OpenAI, Anthropic, Google, DeepSeek, Ollama or any other vendor with a permanent tier. Deployment configuration owns that mapping and can change it without changing orchestration semantics.

Important: a consumer subscription is not automatically API credit. A ChatGPT/Claude/Gemini subscription may be `ZERO_OR_INCLUDED` only when Loop42 actually has a callable, permitted harness covered by that plan. A separately billed API remains metered.

## Visible escalation

Routing chooses exactly one provider for one attempt. It never performs hidden fallback.

A retry/recovery decision may call routing again with the previous profile explicitly excluded or with a stronger requested role such as `recovery`. That produces a new visible Loop42 attempt.

This keeps the intended economics:

```
free/local/already included
        ↓ if sufficient
normal execution
        ↓ only after evidenced failure or stronger role
metered specialist / recovery worker
```

Actual provider quality should come from Loop42 measurements (for example pass rate, retries and cost per verified task), not from a vendor name baked into the core.
