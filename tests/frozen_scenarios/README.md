# Frozen scenarios

Reusable Loop42 evaluation scenarios live here.

Scenarios must pin their input basis and distinguish verified evidence from simulated fixtures. CORA-specific scenarios may be mirrored here only after their generic boundary is explicit.

## CORA context/harness equivalence v1

`cora_context_equivalence_v1.json` freezes the first extracted generic Factory surface against:

- repository: `DeepWolf42/C.O.R.A.`
- revision: `665bdd49724f27258ca4633b0dc5fa8fbb9ae602`
- `tools/project_context.py` blob: `4d187d6c840b7247fc43ebb98ee288eed6eac1ab`
- `tests/test_project_context.py` blob: `a994328aaba9b86df43774c845838e9ed7e92eac`
- `docs/CORA_FACTORY_MATRIXLOOP.md` blob: `a355c96a89938caad6ff82fbd200295a5aeddeef`
- `docs/CHATGPT_FIRST_ARCHITECTURE.md` blob: `1cbad4b85822a8ce60757ee06427f06256e33ac0`

The suite verifies only the generic boundary: exact/deduplicated context capture, stale-basis rejection, safe source paths, checkpoint replay/writer guards, bounded local-model transport, no second product truth, Matrixloop stop behavior and external-reviewer non-authority.

CORA product state, Arthur, printer/slicer/material/HIL behavior and CORA Recovery ownership are explicitly outside this frozen suite.

## Deviation rule

A frozen failure is treated as a regression unless the behavior change is explicit, the expected scenario is deliberately revised, and affected consumer evidence is re-run against the new exact revision. Passing a frozen suite never authorizes automatic deletion of predecessor material.
