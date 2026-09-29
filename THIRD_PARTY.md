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
