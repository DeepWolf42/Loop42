# Harness tools

Reusable provider/harness adapters and capability checks.

## Implemented

`ollama_worker.py` is a thin optional local Ollama adapter over the generic Loop42 project snapshot.

It:

- accepts only plain loopback HTTP endpoints;
- refuses redirects;
- checks the installed local model inventory before chat;
- refuses implicit model download;
- sends one non-streaming proposal-only request;
- returns the exact snapshot fingerprint + Git HEAD with the proposal;
- grants no checkpoint, Git, external-service or physical-machine authority.

Provider-specific behavior stays here. Generic Matrixloop/context rules do not depend on Ollama.
