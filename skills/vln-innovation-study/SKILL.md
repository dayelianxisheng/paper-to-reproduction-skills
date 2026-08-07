---
name: vln-innovation-study
description: Analyze VLN, VLN-CE, ObjectNav, and embodied-navigation papers from the local Zotero VLN collection or user-supplied sources by tracing innovation lineage, preparing auditable source bundles, applying a fixed ten-dimension framework, explaining only innovation-bearing mathematics deeply, separating evidence from inference and hypotheses, maintaining concise human-facing learning notes, auditing causal mechanism demos, and developing testable research ideas. Use when reading, comparing, reviewing, reproducing, or developing research ideas from embodied-navigation papers, or when updating the linked local VLN-paper knowledge repository. Do not use for generic paper summaries outside embodied navigation.
---

# VLN Innovation Study

Turn paper reading into an accumulated technical lineage instead of isolated summaries. For every paper, establish:

`previous paradigm -> bottleneck -> changed mechanism -> mathematical reason -> causal evidence -> dependency/boundary -> later inheritance or replacement`

## Resolve the linked repository

1. Prefer the current Git repository when its `origin` resolves to `dayelianxisheng/VLN-paper`.
2. Otherwise use `/home/zq/resource/code/emb_ai/mobile_robot/clone/VLN-paper` when it exists.
3. Verify the root with `git rev-parse --show-toplevel` and inspect `git remote -v` before writing.
4. Treat `git@github.com:dayelianxisheng/VLN-paper.git` as the canonical remote.
5. Preserve unrelated or untracked files. Do not commit, push, pull, or rewrite history unless the user explicitly requests it.

Read [references/repository-contract.md](references/repository-contract.md) before initializing folders, choosing output paths, or changing repository structure. Run `scripts/init_workspace.py --repo <repo-root>` only when the required directories are missing; it never creates note content.

## Select the reading depth

Choose one depth before analysis:

- `FAST`: screen the task, predecessor paradigm, bottleneck, primary innovation, main evidence, and value of deeper reading.
- `STANDARD`: default for important branch papers; add full dataflow, innovation-bearing math, training/inference distinction, causal ablation, dependencies, cost, and a demo idea.
- `DEEP`: reserve for lineage-defining papers or planned reproduction; add derivation, code-to-equation mapping when code exists, predecessor/successor comparison, reproduction requirements, and a controlled minimum experiment.

Unless the user selects a depth, use `STANDARD`.

## Acquire and qualify evidence

When the user supplies a focal source explicitly, use it. Otherwise resolve papers from the local Zotero `VLN` collection and its descendants. Read [references/zotero-source.md](references/zotero-source.md) before querying Zotero, resolving attachments, or choosing among duplicate PDFs.

Use evidence sources in this order:

1. Explicit local paper PDF or source supplied by the user.
2. Original PDF resolved from the local Zotero `VLN` collection.
3. Official paper, arXiv, or OpenReview page for metadata or source verification.
4. Official project or repository for implementation details.
5. External literature only for historical context, later inheritance, or claim verification.

For a PDF-based `STANDARD` or `DEEP` reading, run `scripts/prepare_vln_source.py` before drafting. Keep its `source_bundle.json` and extracted text in the script's cache directory, never in `notes/`. Use the resulting locator mode:

- `page-grounded`: PDF page anchors are reliable.
- `structure-grounded`: cite sections, figures, tables, or equations; do not trust extracted page indices.
- `source-limited`: state what is unavailable and do not invent unseen methods, experiments, or locators.

Read [references/evidence-workflow.md](references/evidence-workflow.md) before preparing a source bundle, calibrating causal language, auditing a completed analysis, or proposing a research idea.

Do not silently replace missing paper evidence with general knowledge. Mark substantive claims as:

- `AUTHOR`: explicitly supported by the focal paper.
- `LITERATURE`: supported by another identified paper or source.
- `INFERENCE`: mechanism-level interpretation made during analysis.
- `HYPOTHESIS`: a falsifiable but unverified research proposition.
- `USER`: a constraint, observation, or claim supplied by the user and not independently verified.

Keep a paper's own historical or novelty framing distinct from externally verified literature history. Record page, section, equation, table, or figure anchors only when the locator mode supports them. If the focal paper is unavailable, request its path or URL instead of inventing details.

## Analyze one paper

1. Identify the task setting, assumptions, inputs, action space, metrics, and privileged information.
2. Reconstruct the previous mainstream pipeline and the specific contemporary bottleneck.
3. Assign exactly one primary innovation layer and no more than two secondary layers:
   - Task & evaluation
   - Data & supervision
   - Representation & memory
   - Model architecture
   - Training method
   - Inference & planning
   - Action & control
4. State what changed from the closest predecessor. Do not promote standard backbones, standard cross-entropy, or plumbing to primary innovation.
5. Reconstruct the complete dataflow without copying the method figure:

   `observation -> perception encoder -> history/map update -> language-vision fusion -> decision/planning -> controller -> action -> new observation`

6. For each nontrivial block, record its input, output, persistent state, and role in addressing the bottleneck.
7. Separate training-only data, supervision, and privileged information from inference-time state and behavior.
8. Find the closest causal evidence, preferring core-mechanism ablations over SOTA rank.
9. Record sensors, external models, compute, memory, latency, environment assumptions, robustness limits, and reproduction constraints.
10. Classify cross-paper inheritance as `inherited`, `extended`, `replaced`, `challenged`, or `transferred`.

Read [references/ten-dimension-framework.md](references/ten-dimension-framework.md) for the complete checklist before finalizing a paper note.

## Explain mathematics selectively

Classify each equation:

- `MUST-DERIVE`: changes method behavior and carries the innovation.
- `UNDERSTAND-ROLE`: standard mechanism required to follow the pipeline.
- `SKIP`: routine detail that does not change the central conclusion.

For each `MUST-DERIVE` formula, explain in this order:

1. inputs and variables;
2. computation;
3. output;
4. difference from the closest baseline;
5. why the difference should address the stated bottleneck.

Give the geometric or probabilistic intuition before algebraic detail. Never derive equations merely because they appear in the paper.

## Judge experimental evidence

Prefer evidence in this order:

1. ablation removing the core mechanism;
2. controlled replacement with data and model capacity held fixed;
3. robustness or generalization test targeting the claimed bottleneck;
4. cost, latency, or memory trade-off.

State both what the evidence supports and what it does not prove. Explicitly flag gains confounded by stronger encoders, extra data, larger models, privileged supervision, closed models, or changed evaluation settings.

Use `reports`, `observes`, `supports`, or `suggests` unless the experiment directly identifies causality. Use `necessary`, `sufficient`, `causes`, or `proves` only when the design and controls justify that strength.

## Develop a research idea

Accept an idea only when it passes all of these gates:

1. trace it to an identified limitation, failed case, or unresolved ablation;
2. state a falsifiable `HYPOTHESIS`;
3. define the exact mechanism delta from the closest baseline;
4. specify a controlled minimum experiment, metric, expected result, and falsifying result;
5. state the compute/data budget and at least two plausible failure modes;
6. verify prior art before calling the idea novel.

Keep idea generation separate from claims about what the focal paper established.

## Design or implement a demo

Assign `HIGH`, `MEDIUM`, or `LOW` demo suitability. Keep these levels distinct:

- `Mechanism Demo`: expose why the mechanism behaves differently.
- `Minimum Experiment`: compare baseline and new mechanism under controlled conditions.
- `Paper Reproduction`: reproduce the original task, data, model, and metrics.

Never label a mechanism demo as a reproduction. Read [references/demo-principles.md](references/demo-principles.md) before planning or implementing a demo.

When implementation is requested:

1. Define a baseline failure case first.
2. Change only the studied mechanism; keep environment, inputs, seeds, and metrics fixed.
3. Prefer Python with NumPy and Matplotlib or networkx; use a heavy simulator only when necessary.
4. Fix random seeds and expose configuration explicitly.
5. Produce at least one visual artifact and one quantitative metric.
6. Add a Markdown README stating what the demo proves and does not prove.
7. Place code in `demos/<stage>_<mechanism>/`.
8. Use Chinese titles, labels, legends, annotations, and summary text in generated visualizations unless the user requests another language.
9. Run `scripts/audit_vln_demo.py <demo-directory>` and resolve every error before presenting the demo as complete.

## Maintain the knowledge repository

Treat `notes/` as the user's study notebook, not agent storage.

- Default to one cohesive note per user-defined learning path: `notes/<NN>_<path>.md`.
- Add only explanations, comparisons, evidence, formulas, diagrams, conclusions, and questions that help the user learn or review.
- Merge relevant paper evidence and cross-paper mechanism evolution into the path note instead of fragmenting them into separate index, paper, mechanism, status, or checklist files.
- Do not create YAML metadata, empty section skeletons, paper indexes, innovation maps, progress databases, research-question placeholders, or validation artifacts unless the user explicitly requests them.
- Do not persist internal reasoning, evidence bookkeeping, future placeholders, or content the user has not reached yet.
- Keep demos under `demos/`, never under `notes/`.

Use concise Chinese explanations and retain the English technical term on first use. Use Mermaid only when it materially clarifies dataflow or lineage. Record page, table, figure, equation, or section anchors next to claims that the user may want to verify.

After changing a path note, run:

```bash
python <skill-root>/scripts/audit_vln_note.py \
  --profile path-note \
  --source-bundle <cache>/source_bundle.json \
  <repo-root>/notes/<path-note>.md
```

Treat warnings as review prompts. Resolve errors before considering the note update complete. Keep audit reports outside the linked repository.

## Teach interactively

Unless the user requests a full report:

- teach no more than three self-contained knowledge points per response;
- stop after the current batch;
- continue from the next unresolved point when the user sends `1`;
- reset the teaching batch when the user supplies a new paper;
- avoid repeating covered points unless requested.

Update the path note only with material already taught, agreed, or explicitly requested. Do not prefill future lessons.

## Completion gate

Complete one paper analysis only when the working analysis has established:

- one primary innovation layer and at most two secondary layers;
- at least one explicit predecessor relationship;
- the strongest available causal evidence with source anchors;
- equation classifications and required derivations;
- dependencies, cost, and boundaries;
- a demo-suitability rating;
- a one-sentence historical position;

Write only the subset that is useful for the user's current learning path into `notes/`.

For `DEEP`, also require a code-to-equation mapping or a minimum-experiment plan.

For a completed `STANDARD` or `DEEP` paper analysis, store a concise structured working record beside the cached source bundle and run:

```bash
python <skill-root>/scripts/audit_vln_note.py \
  --profile working-analysis \
  --source-bundle <cache>/source_bundle.json \
  <cache>/working-analysis.md
```

The working record contains evidence-backed conclusions, not hidden chain-of-thought. Resolve every error before marking the paper complete. Do not copy the full record or its audit report into `notes/`; persist only the useful material allowed by the repository contract.
