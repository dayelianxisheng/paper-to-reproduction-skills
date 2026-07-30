---
name: evaluate-research-project
description: Audit whether a machine-learning, robotics, VLN, ROS, simulator, or research-code project can run on the current machine; identify hard and soft dependencies; assess CUDA, PyTorch, ROS, simulator, dataset, checkpoint, GUI, headless, inference, evaluation, training, and cloud requirements; and produce an evidence-based local-readiness report. Use before installing or reproducing a paper project, when diagnosing environment compatibility, or when deciding whether local hardware or a server is required.
---

# Evaluate Research Project

Audit the repository and current machine without changing either environment.
Base conclusions on direct evidence, distinguish facts from inferences, and leave
unknowns explicit.

## Safety boundary

- Audit before installing, uninstalling, upgrading, or downgrading anything.
- Do not use `sudo`, modify project source, or alter the active environment.
- Do not download datasets, checkpoints, containers, simulators, or large assets.
- Do not launch full training, full evaluation, or an interactive simulator.
- Ask before compiling, opening a GUI, running a long test, consuming material
  GPU resources, or executing commands that may change state.
- Allow only repository inspection, host inspection, cheap read-only commands,
  and writes below the chosen audit output directory.
- Never expose tokens, passwords, API keys, credential values, or license keys.
  Report only whether a credential appears required or available.

## Required references

Read [references/dependency-evidence-schema.md](references/dependency-evidence-schema.md)
before classifying dependency evidence.

Read [references/robotics-vln-readiness.md](references/robotics-vln-readiness.md)
only when the repository involves VLN, embodied AI, ROS, robotics, simulation,
3D perception, or custom CUDA operations.

Use [references/report-template.md](references/report-template.md) when writing
the final report.

## Audit workflow

### 1. Establish scope and provenance

Resolve the repository root, requested reproduction goal, operating system, and
intended workflow. Record the current Git commit, branch, remotes, dirty state,
submodules, tags, and Git LFS use when Git is available.

Determine whether the repository is official, a maintained fork, or a third-party
implementation using evidence from the paper, project page, authors, release
metadata, and repository history. Do not infer official status from the name alone.

Classify the requested reproduction level:

- `L0`: static inspection only;
- `L1`: imports and cheap tests;
- `L2`: released-checkpoint inference or demo;
- `L3`: paper-aligned evaluation;
- `L4`: fine-tuning or reduced training;
- `L5`: full training and benchmark reproduction.

### 2. Run the non-destructive probe

Run:

```powershell
python "<skill-dir>\scripts\audit_env.py" `
  --repo-root "<repository-root>" `
  --output-dir "<repository-root>\artifacts\local_readiness"
```

On POSIX systems, use `python3`. The probe must create:

- `environment_probe.json`;
- `dependency_evidence.json`;
- `commands_to_verify.sh`;
- `commands_to_verify.ps1`.

Treat probe output as raw evidence. Inspect its command return codes, truncation
flags, scan limits, and warnings before using it.

### 3. Reconcile repository requirements

Inspect and reconcile evidence from:

- README files and documentation;
- `requirements*.txt`, constraints, Conda environment files;
- `pyproject.toml`, `setup.py`, `setup.cfg`, Poetry, uv, and Pipenv files;
- Dockerfiles, Compose files, devcontainers, and CI workflows;
- installation and build scripts;
- source imports, runtime assertions, and version checks;
- ROS manifests, `.repos`, rosdep, CMake, and colcon files;
- simulator configs, launch files, and rendering options;
- CUDA/C++ extension build files;
- dataset, checkpoint, credential, license, and asset instructions.

For every material dependency, preserve:

- component and version constraint;
- source path and line or section;
- evidence type;
- `hard`, `recommended`, `optional`, or `unknown` classification;
- confidence;
- reason and conflicting evidence.

Treat a version as hard only when strong evidence supports it, such as an exact
constraint or lock, runtime assertion, compiled ABI, ROS/Ubuntu pairing,
simulator/plugin coupling, official CI/container image, checkpoint architecture,
or required API use. Treat README command examples as recommendations unless
corroborated.

### 4. Compare with the current machine

Compare, without conflating:

- NVIDIA driver CUDA capability reported by `nvidia-smi`;
- installed CUDA toolkit reported by `nvcc`;
- CUDA version against which PyTorch was compiled;
- PyTorch runtime CUDA availability and device capability.

Assess OS, architecture, WSL/container status, CPU, RAM, swap, disk, Python
interpreters, environment managers, compilers, build tools, GPU/VRAM, cuDNN
indicators, ROS, containers, simulators, rendering stack, datasets, checkpoints,
licenses, and credentials.

Mark a requirement `UNKNOWN` when the probe could not safely determine it. Do
not turn absence from `PATH` into proof that software is not installed elsewhere.

### 5. Run only cheap validation

Start with syntax checks, import/version checks, config parsing, and unit tests
that require no external assets. Run model construction, checkpoint loading,
one tiny episode/batch, or a headless render only when assets already exist and
the action is clearly cheap. Obtain approval otherwise.

For every command, record:

- exact command and working directory;
- start time, duration, return code, and timeout;
- concise stdout and stderr;
- whether the result is verified, inferred, or inconclusive.

Do not hide failures or replace them with a generic summary.

### 6. Issue separate workflow verdicts

Assess independently:

1. imports and unit tests;
2. released-checkpoint inference;
3. one-episode or small-split evaluation;
4. full benchmark evaluation;
5. full training;
6. interactive simulator visualization;
7. headless training, evaluation, and rendering;
8. ROS or real-robot deployment.

Use only:

- `PASS`;
- `PASS_WITH_LIMITS`;
- `BLOCKED`;
- `UNKNOWN`;
- `NOT_APPLICABLE`.

Attach evidence to every verdict. Never collapse the workflows into one generic
yes/no.

### 7. Analyze GUI and headless operation

Classify each applicable workflow as:

- `NATIVE_HEADLESS`;
- `EGL_OR_OSMESA`;
- `XVFB`;
- `GUI_REQUIRED`;
- `UNKNOWN`.

State whether training, evaluation, and rendering can run without a desktop;
whether cloud-trained checkpoints can be copied back for local inference; and
whether inference requires the simulator or only model dependencies.

### 8. Decide whether cloud resources are justified

Recommend cloud or a server only when local hardware, operating-system coupling,
runtime duration, or unavailable dependencies justify it. Separate:

- local inference feasibility;
- local evaluation feasibility;
- local full-training feasibility.

When relevant, provide:

- minimum smoke-test profile;
- recommended reproduction profile;
- full-training profile.

For each profile, specify OS, CPU cores, RAM, GPU and VRAM, disk, driver/toolkit
constraints, display requirements, and suitability for spot/preemptible use.
Label unverified memory or runtime values as estimates and explain their basis.

### 9. Write the audit artifacts

Write below `artifacts/local_readiness/`:

```text
environment_probe.json
dependency_evidence.json
LOCAL_READINESS_REPORT.md
commands_to_verify.sh
commands_to_verify.ps1
```

Use the report template and preserve links to exact evidence. Add safe commands
that resolve unknowns; do not turn them into an installation script.

Choose one final classification:

- `READY_LOCAL`;
- `READY_LOCAL_WITH_LIMITS`;
- `READY_HEADLESS_SERVER`;
- `CLOUD_RECOMMENDED_FOR_TRAINING`;
- `BLOCKED_BY_HARD_DEPENDENCY`;
- `INSUFFICIENT_EVIDENCE`.

## Final response

Lead with the final classification. Then report only:

- top blockers;
- verified hard dependency versions;
- whether cloud resources are needed;
- whether headless training and local inference are feasible;
- paths to the audit artifacts.

Do not install or change anything unless the user separately approves an
installation or remediation plan.
