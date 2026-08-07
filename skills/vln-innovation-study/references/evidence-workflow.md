# Evidence Preparation and Audit

Use this workflow for `STANDARD` and `DEEP` paper analysis. It creates auditable working artifacts without adding agent bookkeeping to the user's `notes/`.

## 1. Prepare one anchor source

Resolve candidate PDFs according to `zotero-source.md`, then run:

```bash
python <skill-root>/scripts/prepare_vln_source.py \
  --pdf <candidate-1.pdf> \
  --pdf <candidate-2.compare.pdf>
```

The script:

- validates PDF headers and hashes every candidate;
- collapses byte-identical duplicates;
- prefers one untransformed original over bilingual or translated reading aids;
- refuses to choose silently when multiple distinct originals remain;
- extracts normalized text when Poppler or PyMuPDF is available;
- inventories section, figure, table, and equation anchors;
- writes `source_bundle.json` and `paper.txt` under the user cache directory.

Use `--anchor <path>` to resolve a genuine ambiguity. Never choose an anchor by file size alone.

## 2. Obey the locator mode

### `page-grounded`

The selected source is an original PDF, its page count is known, and extracted page boundaries agree with that count. PDF page anchors are allowed.

### `structure-grounded`

Text and structural anchors are usable, but PDF page indices are not authoritative. Cite named sections, figures, tables, or equations. Visually inspect the original PDF before adding a page number.

After visual inspection confirms every page anchor in the audited file, add `--verified-page-anchors` to the note-audit command. This override is never valid for `source-limited` material.

### `source-limited`

The available source is partial, unreadable, or lacks sufficient text. State the limitation. Do not infer unseen architectural details, ablations, numerical results, or locators.

The source bundle is an internal evidence artifact. Keep it under the default cache root or another directory outside the linked `VLN-paper` repository.

## 3. Separate provenance

Use these labels in the working analysis:

- `AUTHOR`: the focal paper explicitly states or shows the claim.
- `LITERATURE`: an identified external source supports the claim.
- `INFERENCE`: mechanism-level interpretation derived from available evidence.
- `HYPOTHESIS`: a falsifiable proposition not yet established.
- `USER`: information supplied by the user and not independently verified.

Treat “the paper says it is first” as `AUTHOR`, not verified literature history. Use `LITERATURE` for novelty or historical positioning only after checking identified external sources.

If sources disagree, record the conflict and the source boundaries. Do not silently select the convenient version.

## 4. Calibrate claim strength

Prefer verbs that match the design:

- `reports`: the paper provides the result;
- `observes`: an association or measured pattern appears;
- `supports`: a controlled comparison is consistent with the mechanism;
- `suggests`: evidence is indirect or confounded.

Reserve necessity, sufficiency, causation, and proof language for experiments that manipulate the claimed mechanism, hold relevant alternatives fixed, and measure the claimed outcome. Always state what the strongest experiment does not establish.

## 5. Audit two different artifacts

### Working analysis

For a completed `STANDARD` or `DEEP` reading, create a concise temporary Markdown record beside `source_bundle.json`. Include:

- primary and secondary innovation layers;
- closest predecessor and changed mechanism;
- evidence labels and strongest causal result;
- equation classification;
- training/inference boundary;
- dependencies, cost, and limitations;
- demo suitability;
- one-sentence historical position.

Run:

```bash
python <skill-root>/scripts/audit_vln_note.py \
  --profile working-analysis \
  --source-bundle <cache>/source_bundle.json \
  <cache>/working-analysis.md
```

This record is a compact evidence ledger, not hidden reasoning and not a user note.

### User path note

The path note intentionally contains only material already taught or requested. Audit it with:

```bash
python <skill-root>/scripts/audit_vln_note.py \
  --profile path-note \
  --source-bundle <cache>/source_bundle.json \
  <repo-root>/notes/<path-note>.md
```

This profile checks unsafe locators, placeholders, empty sections, prohibited index-style outputs, and excessive fragmentation without demanding all ten dimensions.

## 6. Gate research ideas

Before presenting an idea as a research direction, record:

1. the exact limitation or failed case that motivates it;
2. a falsifiable `HYPOTHESIS`;
3. the mechanism delta from the closest baseline;
4. controlled variables and the one changed factor;
5. success metric and falsifying outcome;
6. minimum data, compute, simulator, and hardware budget;
7. at least two reasons the idea may fail;
8. prior-art status.

Do not use “novel”, “first”, or “unexplored” until an explicit prior-art search supports that wording.
