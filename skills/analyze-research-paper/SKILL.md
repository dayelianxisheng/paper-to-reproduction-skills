---
name: analyze-research-paper
description: Analyze a research paper as an evidence-backed reproduction specification; extract task, method, architecture, equations, datasets, training, inference, metrics, results, resources, and missing details; search official project pages, GitHub, Hugging Face, releases, datasets, and pretrained checkpoints; and align paper claims with repository code, configs, commands, and assets. Use when reading a paper deeply, checking whether official or third-party pretrained weights exist, combining paper and project analysis, or preparing a staged reproduction plan.
---

# Analyze Research Paper

Turn a paper into an evidence-backed, executable reproduction specification.
Analyze the paper alone when no project is available, and combine paper, code,
config, model-card, and release evidence when a project exists.

## Safety and evidence rules

- Separate `VERIFIED`, `INFERRED`, `ESTIMATED`, and `UNKNOWN`.
- Cite paper page/section/table/figure/equation and repository path/line/config
  key for every material conclusion.
- Preserve conflicts between the paper, supplement, code, configs, model cards,
  and README instead of silently choosing one.
- Prefer official publication, author, project, repository, release, and model
  sources. Label third-party implementations and checkpoints explicitly.
- Do not download large datasets or weights, accept licenses, log in, expose
  tokens, install dependencies, or execute untrusted project code without
  separate user approval.
- Treat the bundled scanner as candidate discovery, not final interpretation.

## Required references

Read [references/analysis-schema.md](references/analysis-schema.md) before
recording evidence or writing `reproduction_spec.json`.

Read
[references/online-weight-search.md](references/online-weight-search.md) when
internet search, project discovery, or pretrained-weight verification applies.

Read [references/vln-analysis.md](references/vln-analysis.md) only for VLN,
embodied AI, navigation, simulator, or robot papers.

Use [references/report-template.md](references/report-template.md) to write the
final artifacts.

## Workflow

### 1. Establish identity and scope

Resolve:

- exact title, authors, DOI/arXiv ID, official publication venue and year;
- paper, supplement, appendix, project page, and version relationship;
- requested reproduction level:
  - `L0`: understand the paper;
  - `L1`: import/model-construction checks;
  - `L2`: released-checkpoint inference;
  - `L3`: paper-aligned evaluation;
  - `L4`: fine-tuning or reduced training;
  - `L5`: full training and benchmark reproduction;
- available project URL or local repository and desired analysis depth.

If publication year differs from the first preprint year, record both. Identify
the exact paper revision before comparing it with code.

### 2. Extract the paper as structured evidence

Read the complete paper and relevant supplement, not only the abstract.
Extract:

1. research question, task definition, assumptions, and contributions;
2. inputs, outputs, observations, actions, and success conditions;
3. architecture modules, data flow, equations, algorithms, and tensor roles;
4. objectives, losses, rewards, optimization, and training stages;
5. datasets, versions, splits, preprocessing, augmentation, and licenses;
6. inference, search, stopping, post-processing, and runtime behavior;
7. metrics, evaluation protocol, baselines, seeds, and statistical treatment;
8. main results, ablations, robustness, failure cases, and limitations;
9. software, hardware, assets, checkpoints, and compute requirements;
10. omissions, ambiguous values, contradictions, and reproduction risks.

Do not confuse a dataset or task benchmark with a model name. Reconstruct
pseudocode or data flow when the paper spreads a procedure across prose,
figures, equations, and appendices, but mark reconstruction as inferred.

### 3. Search current official sources

When internet access is allowed, search the exact title, acronym, identifier,
authors, and project name. Inspect:

- official proceedings, paper page, supplement, and author project page;
- repository linked by the paper or authors;
- repository README, docs, branches, tags, releases, issues, and archived state;
- Hugging Face Models, Datasets, and Spaces;
- official dataset pages, model zoos, and release storage.

Use current primary sources for claims that may change, and cite direct URLs.
Search Hugging Face even when the paper predates the Hub: official organizations
may have published weights later.

### 4. Determine pretrained-weight availability

Distinguish:

- generic backbone/foundation weights;
- intermediate pretraining checkpoints;
- final task or benchmark checkpoints;
- fine-tuned checkpoints;
- adapter/LoRA/delta weights;
- quantized, converted, or third-party derivatives.

For each candidate, record owner, official status, provider, URL, revision or
commit, filenames, visible sizes, format, license, gated access, architecture
and config compatibility, required preprocessing/tokenizer, and evidence.

Choose one overall status:

- `AVAILABLE_VERIFIED`;
- `AVAILABLE_RESTRICTED`;
- `ANNOUNCED_NOT_FOUND`;
- `THIRD_PARTY_ONLY`;
- `BROKEN_OR_REMOVED`;
- `NOT_RELEASED`;
- `UNKNOWN`.

A matching Hugging Face repository name is not proof of official status. Verify
it through the paper, authors, project page, official repository, or institution.
Do not describe backbone-only weights as a released task checkpoint.

### 5. Inspect the project

If a local repository exists, run:

```powershell
python "<skill-dir>\scripts\inspect_project_evidence.py" `
  --repo-root "<repository-root>" `
  --output-dir "<repository-root>\artifacts\paper_analysis" `
  --paper-title "<exact title>" `
  --paper-id "<DOI or arXiv ID>"
```

On POSIX, use `python3`. Inspect the generated `project_evidence.json` and
`weight_evidence.json`, then verify candidates against their source lines.

Also inspect manually:

- repository provenance, commit, branches, tags, submodules, and Git LFS;
- installation/dependency files and supported platform;
- model definitions, forward path, losses, trainer, evaluator, and data loaders;
- configs, defaults, overrides, seeds, and experiment scripts;
- inference, evaluation, training, visualization, and deployment entry points;
- local/remote checkpoints, feature files, data, and license requirements.

If only a remote repository is available, inspect it read-only online. Do not
claim source-level alignment without accessing the relevant revision.

### 6. Align paper and project

Create a row for every important paper component, algorithm step, dataset,
hyperparameter, metric, and workflow. Map it to:

- source path and symbol;
- config key and default;
- command or entry point;
- checkpoint or asset;
- implementation commit/revision.

Classify each row:

- `EXACT_MATCH`;
- `IMPLEMENTED_WITH_DIFFERENCES`;
- `PAPER_ONLY`;
- `CODE_ONLY`;
- `NOT_ENOUGH_EVIDENCE`.

Explain the practical impact of each difference on checkpoint loading,
inference, metric comparability, evaluation, and training. Pay special attention
to code defaults that differ from paper tables, post-publication changes,
unreleased preprocessing, and evaluation scripts with hidden assumptions.

### 7. Build the reproduction specification

Translate the combined evidence into:

- minimal inputs and assets;
- exact environment and dependency evidence;
- inference, evaluation, and training commands or unresolved placeholders;
- expected outputs and paper target metrics;
- resource requirements with measured versus estimated values;
- blockers, unknowns, and safe verification steps;
- staged plan from `L0` through the requested level.

Do not invent a command that the repository does not support. Hand environment
feasibility to `$evaluate-research-project` after the paper/project requirements
are known.

### 8. Write artifacts

Write below `artifacts/paper_analysis/`:

```text
PAPER_ANALYSIS.md
PAPER_PROJECT_ALIGNMENT.md
reproduction_spec.json
project_evidence.json
weight_evidence.json
```

`project_evidence.json` is required only when a repository was inspected.
`PAPER_PROJECT_ALIGNMENT.md` may state `NOT_ENOUGH_EVIDENCE` when no project is
available, but the paper-only analysis must still be completed.

## Quality gate

Before finishing, confirm:

- every reported number has a paper or project location;
- publication and preprint years are distinguished;
- official and third-party projects/weights are separated;
- weight links were checked recently or marked unverified;
- paper metrics and evaluation-code definitions agree or the conflict is shown;
- missing data, licenses, checkpoints, configs, and hardware are explicit;
- each reproduction level has a feasible, blocked, or unknown verdict;
- the report distinguishes facts, inferences, estimates, and unknowns.

## Final response

Lead with the paper's main contribution, pretrained-weight status, official
project status, and highest feasible reproduction level. Then report the most
important paper-code differences, blockers, and artifact paths.
