# Harness tools

Provider-specific harness adapters live behind Loop42's generic capability and authority contracts.

## Local Ollama adapter

`ollama_worker.py` is a deliberately narrow local adapter. It consumes the exact snapshot produced by the generic context tool and grants the model **proposal-only** authority.

Inspect a request without networking:

```text
python tools/harness/ollama_worker.py --repo /path/to/consumer request --model YOUR_MODEL --prompt "What is the next evidenced step?"
```

Run one local request:

```text
python tools/harness/ollama_worker.py --repo /path/to/consumer run --model YOUR_MODEL --prompt "What is the next evidenced step?"
```

Boundary:

- plain HTTP loopback origin only;
- redirects refused;
- local model inventory checked before chat;
- missing models are refused rather than implicitly downloaded;
- non-streaming response only;
- result is bound to exact snapshot fingerprint and Git HEAD;
- model output cannot checkpoint, commit, push, publish or operate physical systems.

Consumer projects keep their own action/approval policy.

## Extraction provenance

The first adapter was extracted from CORA's guarded local Ollama worker at `DeepWolf42/C.O.R.A.` revision `665bdd49724f27258ca4633b0dc5fa8fbb9ae602`. Product-specific CORA instructions and result schema names were removed. The reusable network/capability boundary is preserved behind the Loop42 harness contract.
