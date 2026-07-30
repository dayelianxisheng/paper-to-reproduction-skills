# Online Project and Pretrained-Weight Search

Use this reference when internet access is allowed or when the user asks whether
code, datasets, model cards, or pretrained weights are available.

## Source priority

Search in this order:

1. official proceedings, paper page, supplement, and author project page;
2. repository linked by the paper or authors;
3. repository releases and documented download locations;
4. Hugging Face model, dataset, and Space pages linked by an official source;
5. author or institution Hugging Face organizations;
6. third-party implementations and mirrors, clearly labeled as third party.

Prefer current primary sources. Cite the exact page supporting every current
availability, license, file, or revision claim.

## Search strategy

Search exact paper title, acronym, arXiv/DOI identifier, first author, and
repository name with:

- `official code`, `project page`, `checkpoint`, `pretrained weights`;
- `site:github.com`;
- `site:huggingface.co/models`;
- `site:huggingface.co/datasets`;
- repository Releases and model-zoo documentation.

On Hugging Face, inspect:

- owner and repository identity;
- model card links back to the paper/project;
- Files and versions, revisions, tags, and commit history;
- filenames, formats, shard counts, and visible sizes;
- architecture/config compatibility;
- framework, task, dataset, and library tags;
- license, gated-access requirements, and usage restrictions;
- whether the artifact is a backbone, pretraining checkpoint, task checkpoint,
  adapter/LoRA, quantized derivative, conversion, or demo-only artifact.

Do not infer official status from a matching name. Corroborate the owner or
artifact through the paper, authors, official project, or official repository.

## Weight availability status

Choose one:

- `AVAILABLE_VERIFIED`: official artifact is reachable and metadata matches;
- `AVAILABLE_RESTRICTED`: official artifact exists but is gated or licensed;
- `ANNOUNCED_NOT_FOUND`: official text promises weights but no artifact is found;
- `THIRD_PARTY_ONLY`: only unofficial conversions or reimplementations exist;
- `BROKEN_OR_REMOVED`: an official link exists but is unavailable;
- `NOT_RELEASED`: an official source explicitly says weights are not released;
- `UNKNOWN`: evidence is insufficient.

Record each artifact's URL, provider, owner, revision/commit, filename, visible
size, format, license, access requirements, model role, expected config, and
supporting source.

## Verification boundary

Metadata lookup and link inspection are read-only. Do not download multi-GB
weights, accept a gated license, log in, or expose an access token without user
approval. Do not execute code from a model repository merely to inspect it.

If a checksum is published, record it. Compute a local checksum only after the
artifact is already present and hashing cost is reasonable.
