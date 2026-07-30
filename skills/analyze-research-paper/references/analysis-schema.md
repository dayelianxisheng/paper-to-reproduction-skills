# Paper Analysis Evidence Schema

Use this schema to keep paper facts, project facts, web findings, inferences, and
unknowns separate.

## Evidence record

Record every material conclusion with:

```json
{
  "claim": "The released checkpoint uses a ViT-B/16 visual encoder.",
  "value": "ViT-B/16",
  "source_type": "paper | supplement | official_project | source_code | config | model_card | release | third_party",
  "source": "URL or repository-relative path",
  "location": "page, section, table, figure, line, key, commit, or revision",
  "confidence": "high | medium | low",
  "status": "VERIFIED | INFERRED | ESTIMATED | UNKNOWN",
  "conflicts": []
}
```

Do not describe a claim as verified without a directly inspectable source.
Preserve conflicting evidence instead of silently selecting one value.

## Paper analysis sections

Capture:

1. bibliographic identity and official publication year;
2. research question, task definition, assumptions, and claimed contributions;
3. inputs, outputs, observations, actions, and success conditions;
4. architecture, modules, data flow, equations, and algorithms;
5. objectives, losses, rewards, optimization, and training stages;
6. datasets, versions, splits, preprocessing, augmentation, and licenses;
7. inference procedure, search, stopping, post-processing, and runtime behavior;
8. metrics, evaluation protocol, baselines, and statistical treatment;
9. main results, ablations, robustness, failure cases, and limitations;
10. software, hardware, assets, checkpoints, and estimated reproduction cost;
11. missing details, contradictions, and open questions;
12. staged reproduction plan.

## Reproduction specification

Write `reproduction_spec.json` with these top-level keys:

```json
{
  "paper": {},
  "task": {},
  "method": {"modules": [], "data_flow": [], "objectives": []},
  "data": {"datasets": [], "splits": [], "preprocessing": []},
  "training": {"stages": [], "hyperparameters": {}, "hardware": {}},
  "inference": {"entrypoint": null, "inputs": [], "outputs": []},
  "evaluation": {"metrics": [], "protocol": [], "baselines": []},
  "weights": {"status": "UNKNOWN", "artifacts": []},
  "project": {"repository": null, "commit": null, "official_status": "UNKNOWN"},
  "paper_project_alignment": [],
  "unknowns": [],
  "reproduction_levels": {}
}
```

Use `null` or `UNKNOWN` when evidence is missing; never fabricate a value to
complete the schema.

## Paper-project alignment

For each important paper component, add a row containing:

- paper claim and paper location;
- implementation status;
- code path, symbol, config key, and commit;
- configuration/value comparison;
- consequence for inference, evaluation, or training;
- confidence and unresolved conflict.

Use only:

- `EXACT_MATCH`;
- `IMPLEMENTED_WITH_DIFFERENCES`;
- `PAPER_ONLY`;
- `CODE_ONLY`;
- `NOT_ENOUGH_EVIDENCE`.

## Analysis completeness

Report coverage separately for method, data, training, inference, evaluation,
weights, project alignment, and resource requirements. A missing project or
unavailable supplement must lower only the affected coverage, not invalidate
the paper-only analysis.
