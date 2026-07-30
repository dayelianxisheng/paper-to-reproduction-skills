---
name: evaluate-research-project
description: Check whether a research-code project can run locally by comparing its core dependencies, assets, and hardware needs with the current machine. Use before installing or reproducing a project.
---

# Evaluate Research Project

Evaluate without changing the project or environment. Do not install packages,
download datasets/weights, compile extensions, or start long jobs unless the
user separately approves them.

## Fast workflow

1. Inspect the README, dependency files, main configs, Docker/CI files, and
   inference/evaluation/training entry points.
2. Identify only material requirements:
   - OS and Python;
   - PyTorch and hard package versions;
   - CUDA/native extensions or simulators;
   - datasets, checkpoints, licenses, and credentials;
   - CPU, RAM, disk, GPU, and VRAM.
3. Check the current machine with cheap read-only commands. Keep separate:
   - CUDA capability reported by `nvidia-smi`;
   - installed toolkit reported by `nvcc`;
   - CUDA version compiled into PyTorch;
   - `torch.cuda.is_available()` and device capability.
4. Compare requirements with the machine. Absence from `PATH` means unknown,
   not proof that software is absent.
5. Give separate verdicts for:
   - released-checkpoint inference;
   - paper-aligned evaluation;
   - training.
6. State the top blockers and the shortest safe next step. Recommend a server
   only when local OS, hardware, or runtime is insufficient.

Use `scripts/audit_env.py` only when the user asks for a detailed audit or a
saved machine-readable report. Default to a concise answer without logs or
artifact files.
