# Paper and Project Analysis Template

Write the final artifacts below `artifacts/paper_analysis/`.

## `PAPER_ANALYSIS.md`

```markdown
# Paper Analysis

## Executive summary

- Paper:
- Publication:
- Task:
- Claimed contribution:
- Official project:
- Pretrained-weight status:
- Target reproduction level:
- Overall reproduction risk:

## Evidence coverage

| Area | Coverage | Strongest source | Important unknown |
|---|---:|---|---|
| Method | | | |
| Data | | | |
| Training | | | |
| Inference | | | |
| Evaluation | | | |
| Weights | | | |
| Project alignment | | | |
| Resources | | | |

## Problem and task definition

## Contributions and novelty

## Method and architecture

Include a component/data-flow description and cite pages, figures, equations,
or algorithms.

## Objectives and training procedure

## Datasets, preprocessing, and licenses

## Inference procedure

## Evaluation protocol and metrics

## Results, ablations, and limitations

## Software and hardware requirements

## Pretrained weights

| Artifact | Role | Official status | Provider/revision | Format/size | License/access | Compatibility | Evidence |
|---|---|---|---|---|---|---|---|

## Open questions and contradictions

## Staged reproduction plan
```

## `PAPER_PROJECT_ALIGNMENT.md`

```markdown
# Paper-Project Alignment

- Repository:
- Commit:
- Official status:
- Paper/project version relationship:

| Paper component or claim | Paper evidence | Code/config evidence | Alignment | Impact | Confidence |
|---|---|---|---|---|---|

## Entry points

| Workflow | Command/config | Required assets | Expected output | Evidence |
|---|---|---|---|---|

## Differences affecting reproduction

## Code-only behavior

## Paper-only or missing implementation
```

## Required machine-readable files

- `reproduction_spec.json`: use `analysis-schema.md`;
- `project_evidence.json`: raw output from the scanner when a local repo exists;
- `weight_evidence.json`: raw plus agent-reviewed weight candidates.

The report must distinguish verified facts, inferences, estimates, and unknowns.
Do not cite the raw scanner as proof when the underlying source line can be
cited directly.
