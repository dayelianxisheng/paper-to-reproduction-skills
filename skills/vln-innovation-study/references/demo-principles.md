# Causal Mechanism Demo Principles

## Select the correct experiment level

### Mechanism Demo

Use a synthetic or controlled setting to expose a behavioral difference caused by one mechanism. Claim only that the mechanism can resolve the constructed failure under the stated assumptions.

### Minimum Experiment

Use a task-shaped dataset or environment, a meaningful baseline, repeated seeds, and task-relevant metrics. Claim a controlled comparison, not paper-level reproduction.

### Paper Reproduction

Match the original task, data splits, observation and action spaces, preprocessing, model, training protocol, evaluation, and reported metrics. Document every unavoidable deviation.

## Decide suitability

- `HIGH`: isolate the mechanism faithfully with small data or simulation and directly measure its intended effect.
- `MEDIUM`: demonstrate representation, planning, memory, or computational behavior, but not reliable navigation quality.
- `LOW`: omit implementation when simplification would change the claimed mechanism, require unavailable proprietary components, or confuse a toy proxy with the paper.

## Define the causal contrast

Write a short contract before coding:

1. Bottleneck: the precise failure being tested.
2. Baseline: the predecessor mechanism expected to exhibit it.
3. Intervention: the single mechanism changed.
4. Controls: environment, observations, seed sequence, model capacity, and budget kept fixed.
5. Outcome: visual and quantitative signals that reveal the difference.
6. Non-claims: conclusions the experiment cannot support.

Reject a proposed demo if the intervention changes several contribution layers at once and no ablation can separate them.

## Implementation standard

- Prefer the smallest faithful implementation.
- Use deterministic seeds and log the full configuration.
- Separate environment generation, baseline, intervention, metrics, and visualization.
- Save raw results in a machine-readable form when multiple seeds are used.
- Report central tendency and variation for stochastic experiments.
- Use identical inputs and budgets for paired comparisons.
- Label plots with units, seed count, and direction of better performance.
- Keep generated artifacts under the demo directory.

## Recommended stage sequence

| Stage | Directory | Intended contrast |
|---:|---|---|
| 1 | `01_discrete_vs_continuous` | graph-constrained success versus continuous-control failure |
| 2 | `02_waypoint_abstraction` | low-level horizon versus temporal action abstraction |
| 3 | `03_online_topological_planning` | local choice versus global memory and backtracking |
| 4 | `04_rgbd_semantic_mapping` | image history versus spatialized semantic memory |
| 5 | `05_belief_map_fusion` | deterministic state versus uncertainty and negative evidence |
| 6 | `06_memory_scaling` | explicit history growth versus compressed streaming state |
| 7 | `07_recovery_and_stop` | one-shot prediction versus verification and recovery |
| 8 | `08_temporal_dynamic_map` | stale static memory versus temporal adaptation |
| 9 | `09_world_model_exploration` | current evidence versus predicted unseen outcomes |

Treat this order as a conceptual dependency chain, not a claim of publication chronology.

## Required README content

Include:

- research question and baseline failure;
- relationship to the focal paper and evidence label;
- environment and controlled variables;
- exact run command and dependencies;
- metric definitions and generated outputs;
- observed result;
- what the demo proves;
- what it does not prove;
- differences from paper reproduction.

## Review risks

Check for:

- hidden extra information available only to the intervention;
- unequal search, compute, action, or observation budgets;
- cherry-picked seeds or scenarios;
- metrics that reward the constructed solution by definition;
- visual examples inconsistent with aggregate results;
- conclusions about navigation quality drawn from representation-only tests;
- use of “reproduction” when the original evaluation contract is not matched.
