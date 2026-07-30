# Local Readiness Report Template

Copy this structure to `artifacts/local_readiness/LOCAL_READINESS_REPORT.md`.
Replace every placeholder with evidence or `UNKNOWN`. Remove sections that are
truly not applicable, but keep all workflow verdict rows.

```markdown
# Local Readiness Report

## Executive verdict

- Final classification: `<CLASSIFICATION>`
- Requested reproduction level: `<L0-L5>`
- Local inference: `<feasibility>`
- Local evaluation: `<feasibility>`
- Local full training: `<feasibility>`
- Headless server path: `<feasibility>`
- Cloud needed: `<no / optional / recommended / required>`
- Evidence timestamp: `<ISO-8601>`
- Repository commit: `<commit or UNKNOWN>`

## Project provenance

| Item | Finding | Evidence | Confidence |
|---|---|---|---|
| Official implementation | | | |
| Repository version | | | |
| License | | | |
| Maintenance status | | | |
| Paper-code alignment | | | |

## Project execution map

| Workflow | Entry command/config | Required assets | Expected output |
|---|---|---|---|
| Imports/tests | | | |
| Checkpoint inference | | | |
| Small evaluation | | | |
| Full evaluation | | | |
| Full training | | | |
| Visualization | | | |
| ROS/deployment | | | |

## Detected environment

Summarize verified host facts. Keep driver CUDA capability, local CUDA toolkit,
PyTorch-compiled CUDA, and PyTorch runtime availability separate.

## Dependency compatibility matrix

| Component | Required | Installed/detected | Classification | Compatibility | Evidence |
|---|---|---|---|---|---|

## Hard version constraints

List only constraints supported by strong evidence. Explain ABI, simulator,
ROS/Ubuntu, checkpoint, or API coupling.

## Recommended and optional dependencies

Separate tested/recommended environments from truly optional features.

## Workflow verdicts

| Workflow | Verdict | Headless class | Evidence | Blocker or limit |
|---|---|---|---|---|
| Imports and unit tests | UNKNOWN | NOT_APPLICABLE | | |
| Released-checkpoint inference | UNKNOWN | UNKNOWN | | |
| One-episode/small evaluation | UNKNOWN | UNKNOWN | | |
| Full benchmark evaluation | UNKNOWN | UNKNOWN | | |
| Full training | UNKNOWN | UNKNOWN | | |
| Interactive visualization | UNKNOWN | GUI_REQUIRED | | |
| Headless train/eval/render | UNKNOWN | UNKNOWN | | |
| ROS or real-robot deployment | UNKNOWN | UNKNOWN | | |

Use only PASS, PASS_WITH_LIMITS, BLOCKED, UNKNOWN, or NOT_APPLICABLE.

## Local hardware sufficiency

Discuss CPU, RAM, swap, disk, GPU, VRAM, compute capability, expected duration,
and which conclusions are measured versus estimated.

## GUI and headless capability

State whether training, evaluation, video rendering, simulator use, and
teleoperation require a desktop, EGL/OSMesa, Xvfb, or a native GUI.

## Cloud or server recommendation

### Minimum smoke-test profile

- OS:
- CPU:
- RAM:
- GPU/VRAM:
- Disk:
- Driver/toolkit:
- Display:
- Spot/preemptible suitability:

### Recommended reproduction profile

- OS:
- CPU:
- RAM:
- GPU/VRAM:
- Disk:
- Driver/toolkit:
- Display:
- Spot/preemptible suitability:

### Full-training profile

- OS:
- CPU:
- RAM:
- GPU/VRAM:
- Disk:
- Driver/toolkit:
- Display:
- Spot/preemptible suitability:

Mark unmeasured values as estimates and explain the basis.

## Minimal reproducible setup plan

Describe an ordered plan only. Do not install or change the environment.

## Tests performed

| Command | Working directory | Return code | Duration | Result |
|---|---|---:|---:|---|

## Blockers, conflicts, and unknowns

| Item | Type | Impacted workflows | Evidence | Safe resolution command |
|---|---|---|---|---|

## Final classification rationale

Choose one:

- READY_LOCAL
- READY_LOCAL_WITH_LIMITS
- READY_HEADLESS_SERVER
- CLOUD_RECOMMENDED_FOR_TRAINING
- BLOCKED_BY_HARD_DEPENDENCY
- INSUFFICIENT_EVIDENCE

Explain why the evidence supports this classification and why stronger or
weaker classifications were rejected.
```
