# Ten-Dimension Paper Framework

Use this checklist to finalize each persistent paper note. Record unknowns explicitly; never complete a field by guessing.

## 1. Task setting and assumptions

- Name the task variant: VLN, VLN-CE, ObjectNav, RxR, zero-shot navigation, or another embodied-navigation setting.
- Record language, visual, depth, pose, map, and goal inputs.
- Record discrete, continuous, waypoint, or low-level action space.
- Record simulator or physical-robot setting, datasets, splits, and metrics.
- Mark privileged information and train-test differences.

## 2. Previous mainstream paradigm

- Identify the closest predecessor family, not just the oldest historical baseline.
- Express its pipeline as dataflow.
- Explain what information it retains, discards, or assumes.
- Cite a focal-paper section or a verified predecessor source.

## 3. Contemporary bottleneck

- State the failure in operational terms: what input condition causes what behavior or metric loss?
- Separate the authors' stated problem (`AUTHOR`) from period context (`LITERATURE`) and interpretation (`INFERENCE`).
- Avoid generic claims such as “poor generalization” without naming the distribution shift or mechanism.

## 4. Innovation layer

- Choose exactly one primary layer from the seven-layer taxonomy.
- Choose at most two secondary layers.
- List conspicuous non-innovations to prevent contribution inflation.
- Explain why the primary layer, rather than an enabling component, carries the paper's central change.

## 5. Full method dataflow

- Trace observation to action and the next observation.
- For every nontrivial module, record input, output, retained state, and role.
- Show when language enters, when maps or memory update, and when planning differs from control.
- Distinguish learned transformations from deterministic algorithms.

## 6. Core mathematical mechanism

- Inventory important equations and label each `MUST-DERIVE`, `UNDERSTAND-ROLE`, or `SKIP`.
- Derive only equations whose changed form causes changed behavior.
- Define tensor or state shapes when needed to understand information flow.
- Compare the mechanism against the closest baseline form.
- Connect the mathematical difference to the stated bottleneck without claiming untested causality.

## 7. Training versus inference

- Record data, labels, auxiliary losses, curriculum, pretraining, and extra supervision.
- Record online state updates, replanning cadence, STOP logic, recovery, and controller behavior.
- Identify teacher forcing, simulator-only signals, or oracle data absent at inference.
- Separate training compute from deployment latency and memory.

## 8. Strongest causal evidence

- Prefer a core-mechanism ablation or controlled replacement.
- Record exact table, figure, section, split, metric, and numerical delta.
- State what variables are controlled and which possible confounders remain.
- Explain what the evidence supports and what it cannot establish.
- Treat overall SOTA as context, not causal proof.

## 9. Dependencies, cost, and boundaries

- List required sensors, pose, depth, maps, external models, APIs, or proprietary systems.
- Record parameter, FLOP, memory, latency, storage, or token costs when available.
- Identify environment assumptions, calibration needs, and sensitivity to noise or dynamics.
- Record missing assets, undocumented preprocessing, licenses, or hardware constraints affecting reproduction.

## 10. Innovation inheritance

- Name at least one predecessor relationship.
- For related or later papers, classify the relation as inherited, extended, replaced, challenged, or transferred.
- Name the exact mechanism transferred or changed; avoid lineage based only on citations.
- Keep publication chronology separate from conceptual dependency order.

## Synthesis outputs

Finish with:

- one sentence locating the paper historically;
- what is worth reproducing and at which experiment level;
- demo suitability (`HIGH`, `MEDIUM`, or `LOW`);
- evidence-backed research openings and the minimum experiment that could test them.

## Completion audit

Before marking `status: complete`, verify:

- Every substantive claim has an evidence label or source anchor.
- The primary innovation is singular and specific.
- Dataflow closes the observation-action loop.
- Training-only information is not attributed to inference.
- The strongest experiment actually manipulates or targets the claimed mechanism.
- Costs and boundaries are as visible as gains.
- The innovation lineage in the user's path note agrees with the current paper analysis.
