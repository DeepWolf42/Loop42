# Third-Party Sources

Loop42 tracks external sources used for architecture, evaluation, harness research, or implementation inspiration.

This file records provenance; listing a source does **not** mean its code is vendored, copied, or license-compatible with a future Loop42 release.

## Factory / harness research

The entries below were carried forward from CORA's verified 2026-09-26 Factory provenance audit when generic Factory ownership moved to Loop42. Their current use is **research / pattern reference only** unless a later file-level record says otherwise.

| Project | Source | License observed in the CORA audit | Loop42 use |
| --- | --- | --- | --- |
| ECC / Everything Claude Code | https://github.com/affaan-m/ECC | MIT | multi-harness, verification, codemap, learning/evolution and security-pattern research |
| wshobson/agents | https://github.com/wshobson/agents | MIT | canonical-source-to-multiple-harness adapter research |
| mattpocock/skills | https://github.com/mattpocock/skills | MIT | skill/workflow structure research |
| OpenAI Codex | https://github.com/openai/codex | Apache-2.0 | harness/tooling and instruction-scope reference |
| Google Gemini CLI | https://github.com/google-gemini/gemini-cli | Apache-2.0 | bounded action-policy pattern: allow / deny / ask_user, priority matching and headless ask->deny; pinned research revision `38700b4b38bf387dafded6c97c3f190d084b49e9`, docs blob `95e65b33bd47e342c644b059e2e7a7c27d171d85`; no Gemini code/runtime imported |
| Aider | https://github.com/Aider-AI/aider | Apache-2.0 | bounded repository-map/context-selection pattern; research revision `5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Loop42 implementation is independent standard-library code, no Aider code/runtime imported |
| OpenAI Agents SDK Python | https://github.com/openai/openai-agents-python | MIT | pre-side-effect guardrail revalidation / approval-resume race pattern; pinned research revision `6862bdfa70a788626a0df5b9c69c8c0e1a2cc441`, no runtime/code imported |
| Ollama | https://github.com/ollama/ollama | MIT | local `/api/chat` structured-output interoperability: documented JSON-schema `format`, non-streaming completion metadata and temperature guidance; docs checked 2026-09-30, upstream revision `1abe35e6e6e777e858bbfbba283667ee8d516801`; Loop42 validation is independently implemented, no Ollama code imported |
| SLSA | https://github.com/slsa-framework/slsa | Community Specification License 1.0 for the referenced specification material | provenance/attestation research for content-bound verification receipts; pinned revision `82b296d49e4c8301e7db565f23620ffe89092a0c`, `spec/provenance.md` blob `769ed89d04dae9fa081eebf5af85777b9d522765`; Loop42 receipt code is independently implemented and no SLSA text/code is copied |
| DSPy | https://github.com/stanfordnlp/dspy | MIT | prompt/evaluation research: compare prompt/program candidates against explicit metrics and validation scenarios; pinned research revision `98a4deebcf5dd30c02ea86a5abc46b8ae877111c`; no DSPy runtime/code imported |
| Promptfoo | https://github.com/promptfoo/promptfoo | MIT | prompt regression/assertion and adversarial-evaluation research; pinned research revision `0e1e076298e1f2fd27fd80fd6a413047293c0eae`; no Promptfoo runtime/code imported |
| Chaos Mesh | https://github.com/chaos-mesh/chaos-mesh | Apache-2.0 | fault-injection/chaos-testing research for deliberate recovery ambiguity scenarios; pinned research revision `c859a9c63164920478099947c8fa730ecb220477`; no Chaos Mesh runtime/code imported |
| mini-SWE-agent | https://github.com/SWE-agent/mini-swe-agent | MIT | small bounded agent-loop/run-budget research |
| Microsoft Agent Framework | https://github.com/microsoft/agent-framework | MIT | workflow/checkpoint/resume research |
| LangGraph | https://github.com/langchain-ai/langgraph | MIT | durable execution/checkpoint/human-interrupt research |
| Intrinsic Core | https://github.com/intrinsic-ai/intrinsic-core | Apache-2.0 | generic architecture/HAL/runtime-boundary research where applicable |
| Anthropic skills repository | https://github.com/anthropics/skills | file/repository-specific; no single root license relied upon | progressive-disclosure/skill-evaluation research only; check a specific file's license before reuse |

No implementation code from these projects is intentionally imported by the current Loop42 v0.1 extraction. The extracted context and bounded Ollama-harness code is project-owned code derived from the already-proven CORA implementation path, with its exact CORA extraction basis recorded in the corresponding Loop42 documentation and frozen scenarios.

## Development / CI tooling

Loop42 currently uses normal GitHub/Python tooling rather than vendoring it:

- `actions/checkout` — MIT; CI pin currently references commit `3d3c42e5aac5ba805825da76410c181273ba90b1` (v7.0.1)
- `actions/setup-python` — MIT; CI pin currently references commit `5fda3b95a4ea91299a34e894583c3862153e4b97` (v7.0.0)
- `gacts/gitleaks` — MIT; CI pin currently references commit `4fd785dcdaf557fda64e05b0ae033b8f7d82fb81` (v1.3). It installs and runs the MIT-licensed `gitleaks/gitleaks` scanner, currently pinned by workflow input to v8.29.1. No scanner or wrapper code is vendored.
- GitHub Dependabot — hosted GitHub service used for grouped GitHub Actions version-update PRs; no Dependabot implementation is vendored in Loop42.
- Python standard library / `unittest` for the v0.1 test surface

A future packaged/distributed Loop42 release must run a fresh dependency/file/license audit instead of treating this source-level list as an SBOM.

## Project-owned assets

- `docs/assets/loop42-mark.webp` — project-owned Loop42 visual asset. Origin/reuse rights were explicitly attested by the operator on 2026-09-29 as created by/for this project rather than sourced from a third party.

## Provenance rule

Before importing or adapting third-party code:

1. record the exact project, source and revision;
2. record the applicable license, including per-file exceptions;
3. distinguish research/reference ideas from copied or adapted implementation;
4. for direct reuse, retain every required notice and source/modification obligation;
5. keep incompatible or uncertain material out of Loop42 core;
6. run a release-specific dependency/file/license audit before publication or distribution.

CORA-specific firmware, slicer, printer and manufacturing-source provenance remains in CORA. Historical Factory entries may remain in CORA for traceability, but current generic Factory provenance is owned here.
