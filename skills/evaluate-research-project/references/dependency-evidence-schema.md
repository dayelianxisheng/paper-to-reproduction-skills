# Dependency Evidence Schema

Use this schema to reconcile raw scanner findings with repository documentation,
runtime behavior, and the current machine. Scanner classifications are
provisional; the final report must reflect agent-reviewed evidence.

## Record fields

Each material dependency record should contain:

```json
{
  "component": "torch",
  "constraint": "==2.1.0",
  "source_path": "requirements.txt",
  "line": 12,
  "section": null,
  "evidence_type": "requirements",
  "classification": "hard",
  "confidence": "high",
  "reason": "Exact project constraint corroborated by a runtime assertion",
  "raw": "torch==2.1.0",
  "conflicts": []
}
```

Use repository-relative paths. Do not place credential values, private URLs, or
secret environment variables in evidence records.

## Classification

### `hard`

Use only when violating the requirement is likely to prevent installation,
loading, execution, or correct results. Strong evidence includes:

- an exact lock or constraints file used by the documented workflow;
- a runtime version assertion;
- a compiled extension or binary ABI requirement;
- a required ROS distribution and Ubuntu pairing;
- a simulator/plugin or engine coupling;
- an official container or CI environment that is the only tested path;
- an API or symbol introduced or removed at a known version;
- checkpoint architecture or serialization coupling;
- a dataset format or benchmark version required for comparable metrics.

An exact pin in an old README command is not hard by itself.

### `recommended`

Use for the authors' tested environment, CI matrix, Docker base image, or setup
example when alternatives may work but are unverified.

### `optional`

Use for extras, visualization-only packages, logging integrations, optional
datasets, development tools, alternative backends, or explicitly guarded imports.

### `unknown`

Use when evidence is incomplete, contradictory, generated heuristically, or
insufficient to distinguish hard from recommended.

## Confidence

- `high`: direct, current, internally consistent evidence tied to the execution
  path being assessed.
- `medium`: authoritative but indirect evidence, such as a tested CI/container
  environment or maintained setup guide.
- `low`: heuristic source-import scan, unversioned prose, stale instructions,
  issue comments, or an inference without a measured run.

Do not use confidence as a substitute for classification.

## Evidence strength

Prefer evidence in this order, while considering freshness:

1. runtime assertions and executed failures;
2. lockfiles, constraints, compiled build metadata, and checkpoint loaders;
3. official CI, containers, release tags, and maintained environment files;
4. package metadata and installation scripts;
5. current README and official documentation;
6. source imports and API usage;
7. issues, forks, comments, and third-party instructions.

Record conflicts instead of silently selecting one version. Explain which
workflow each conflicting requirement belongs to.

## Compatibility comparison

Compare project requirements with:

- host OS and architecture;
- active Python and alternative interpreters;
- installed packages in the intended environment;
- NVIDIA driver capability;
- local CUDA toolkit;
- PyTorch-compiled CUDA and runtime availability;
- compiler and C++ ABI;
- ROS distribution and Ubuntu version;
- simulator and rendering backend;
- dataset, checkpoint, license, and credential availability.

Use `compatible`, `incompatible`, `missing`, `unknown`, or `not_applicable`.
Absence from `PATH` normally means `unknown` or `missing_from_path`, not proof
that software is absent from the machine.

## Facts, inferences, and estimates

- **Verified fact**: directly observed in a file, command result, or existing
  artifact.
- **Inference**: a reasoned conclusion from multiple facts; state the reasoning.
- **Estimate**: an unmeasured resource or duration prediction; state the basis
  and uncertainty.
- **Unknown**: insufficient safe evidence; provide a command that could resolve
  it.

## Secret handling

Report only the requirement or presence of credentials. Redact:

- passwords, access tokens, cookies, private keys, and API keys;
- credentials embedded in repository remotes or URLs;
- full contents of `.env`, authentication files, and license keys.

Do not inspect private key material. Do not emit environment variables outside
the probe's explicit safe allowlist.
