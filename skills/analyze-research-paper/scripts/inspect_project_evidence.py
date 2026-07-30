#!/usr/bin/env python3
"""Collect read-only project evidence for paper-to-code analysis."""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit, urlunsplit


SCHEMA_VERSION = 1
SCRIPT_VERSION = "0.1.0"
DEFAULT_MAX_FILES = 20_000
DEFAULT_MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_RECORDS_PER_KIND = 500

EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "build",
    "dist",
    "artifacts",
    "outputs",
    "output",
    "logs",
    "wandb",
    "data",
    "datasets",
    "checkpoints",
    "weights",
}

TEXT_SUFFIXES = {
    ".md",
    ".rst",
    ".txt",
    ".py",
    ".sh",
    ".ps1",
    ".bat",
    ".cmd",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".ini",
    ".cfg",
    ".conf",
    ".xml",
    ".launch",
    ".repos",
    ".cmake",
}

WEIGHT_SUFFIXES = {
    ".pt",
    ".pth",
    ".ckpt",
    ".safetensors",
    ".onnx",
    ".pkl",
    ".pickle",
    ".npz",
    ".h5",
    ".pb",
    ".tflite",
}

DEPENDENCY_NAMES = {
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "poetry.lock",
    "uv.lock",
    "pdm.lock",
    "pipfile",
    "pipfile.lock",
    "environment.yml",
    "environment.yaml",
    "package.xml",
    "cmakelists.txt",
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
    "devcontainer.json",
}

SECRET_FILE_RE = re.compile(
    r"(?i)(^|[._-])(secret|token|credential|password|passwd|api[_-]?key)"
    r"([._-]|$)"
)
URL_RE = re.compile(r"https?://[^\s<>'\"`]+", re.I)
HF_URL_RE = re.compile(
    r"https?://huggingface\.co/(?:models/|datasets/|spaces/)?"
    r"([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)",
    re.I,
)
HF_CALL_RE = re.compile(
    r"(?:from_pretrained|hf_hub_download|snapshot_download)"
    r"\s*\(\s*(?:repo_id\s*=\s*)?[\"']([^\"']+/[^\"']+)[\"']",
    re.I,
)
ARXIV_RE = re.compile(
    r"(?:arxiv(?:\.org/(?:abs|pdf)/|:?\s*))"
    r"([a-z-]+(?:\.[A-Z]{2})?/\d{7}|\d{4}\.\d{4,5})",
    re.I,
)
DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.I)
ENTRY_RE = re.compile(
    r"^\s*(?:\$|>|PS>)?\s*"
    r"(python(?:3)?|torchrun|accelerate|deepspeed|bash|sh|"
    r"roslaunch|ros2\s+launch|docker\s+run|docker\s+compose)\s+(.+)$",
    re.I,
)
WEIGHT_CONTEXT_RE = re.compile(
    r"(?i)\b(weight|weights|checkpoint|checkpoints|ckpt|pretrain(?:ed|ing)?|"
    r"model zoo|model hub|download model|trained model|safetensors|"
    r"from_pretrained|hf_hub_download|snapshot_download|lora|adapter)\b"
)

METRIC_TERMS = {
    "accuracy",
    "precision",
    "recall",
    "f1",
    "auc",
    "map",
    "miou",
    "iou",
    "bleu",
    "rouge",
    "meteor",
    "cider",
    "wer",
    "cer",
    "perplexity",
    "psnr",
    "ssim",
    "fid",
    "success rate",
    "sr",
    "spl",
    "navigation error",
    "ne",
    "oracle success rate",
    "osr",
    "ndtw",
    "sdtw",
    "cls",
}

DATASET_TERMS = {
    "r2r",
    "rxr",
    "reverie",
    "cvdn",
    "touchdown",
    "matterport3d",
    "hm3d",
    "gibson",
    "imagenet",
    "coco",
    "cityscapes",
    "kitti",
    "nuscenes",
    "waymo",
    "squad",
    "wikipedia",
    "common crawl",
}

SYMBOL_HINT_RE = re.compile(
    r"(?i)(model|agent|policy|planner|navigator|encoder|decoder|transformer|"
    r"dataset|dataloader|environment|simulator|trainer|evaluator|loss|"
    r"train|evaluate|inference|predict|forward|rollout)"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Collect read-only repository, checkpoint, model-hub, command, "
            "dataset, metric, and code-symbol evidence for paper analysis."
        )
    )
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--paper-title", default="")
    parser.add_argument("--paper-id", default="")
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    parser.add_argument(
        "--max-file-bytes", type=int, default=DEFAULT_MAX_FILE_BYTES
    )
    return parser.parse_args()


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def redact_home(value: str) -> str:
    text = str(value)
    home = str(Path.home())
    for variant in (home, home.replace("\\", "/")):
        if variant:
            text = re.sub(re.escape(variant), "<HOME>", text, flags=re.I)
    return text


def sanitize_url(raw: str) -> str:
    value = raw.rstrip(".,);]}:")
    try:
        parts = urlsplit(value)
        hostname = parts.hostname or ""
        if parts.port:
            hostname = f"{hostname}:{parts.port}"
    except ValueError:
        return "<invalid-url>"
    return urlunsplit((parts.scheme, hostname, parts.path, "", ""))


def safe_relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return redact_home(str(path))


def read_text(path: Path, max_bytes: int) -> str | None:
    try:
        if path.stat().st_size > max_bytes:
            return None
        data = path.read_bytes()
    except (OSError, PermissionError):
        return None
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def is_text_candidate(path: Path) -> bool:
    name = path.name.lower()
    if name in DEPENDENCY_NAMES:
        return True
    if name.startswith(("readme", "requirements", "constraints")):
        return True
    if name.startswith("dockerfile"):
        return True
    return path.suffix.lower() in TEXT_SUFFIXES


def is_dependency_file(path: Path) -> bool:
    name = path.name.lower()
    rel = path.as_posix().lower()
    if name in DEPENDENCY_NAMES:
        return True
    if name.startswith(("requirements", "constraints")) and name.endswith(".txt"):
        return True
    if name.startswith(("environment", "conda")) and name.endswith(
        (".yml", ".yaml")
    ):
        return True
    if rel.startswith(".github/workflows/") and name.endswith((".yml", ".yaml")):
        return True
    return False


def provider_for(value: str) -> str:
    lower = value.lower()
    if "huggingface.co" in lower or "hf_hub_" in lower:
        return "huggingface"
    if "github.com" in lower and ("/releases/" in lower or "download" in lower):
        return "github_release"
    if "drive.google.com" in lower:
        return "google_drive"
    if "pan.baidu.com" in lower:
        return "baidu_netdisk"
    if "dropbox.com" in lower:
        return "dropbox"
    if lower.startswith("local:"):
        return "local"
    return "other"


def weight_type_for(value: str) -> str:
    lower = value.lower()
    if any(term in lower for term in ("lora", "adapter", "delta", "peft")):
        return "adapter_or_delta"
    if any(
        term in lower
        for term in (
            "backbone",
            "imagenet",
            "bert",
            "clip",
            "resnet",
            "vit",
            "feature extractor",
            "pretrain",
        )
    ):
        return "backbone_or_pretraining"
    if any(
        term in lower
        for term in (
            "checkpoint",
            "ckpt",
            "model_final",
            "best_model",
            "finetuned",
            "fine-tuned",
            "trained model",
        )
    ):
        return "task_checkpoint"
    return "unknown"


def add_unique(
    destination: list[dict[str, Any]],
    seen: set[tuple[Any, ...]],
    key: tuple[Any, ...],
    record: dict[str, Any],
) -> None:
    if key in seen or len(destination) >= MAX_RECORDS_PER_KIND:
        return
    seen.add(key)
    destination.append(record)


def run_git(repo_root: Path, args: list[str]) -> dict[str, Any]:
    command = ["git", "-C", str(repo_root), *args]
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=8,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "command": [redact_home(part) for part in command],
            "return_code": None,
            "stdout": "",
            "stderr": type(exc).__name__,
        }
    stdout = completed.stdout.decode("utf-8", errors="replace").strip()
    stderr = completed.stderr.decode("utf-8", errors="replace").strip()
    if args[:2] == ["remote", "-v"]:
        stdout = re.sub(
            r"https?://[^\s]+",
            lambda match: sanitize_url(match.group(0)),
            stdout,
        )
    return {
        "command": [redact_home(part) for part in command],
        "return_code": completed.returncode,
        "stdout": redact_home(stdout[:4000]),
        "stderr": redact_home(stderr[:2000]),
    }


def collect_git(repo_root: Path) -> dict[str, Any]:
    probes = {
        "root": run_git(repo_root, ["rev-parse", "--show-toplevel"]),
        "commit": run_git(repo_root, ["rev-parse", "HEAD"]),
        "branch": run_git(repo_root, ["branch", "--show-current"]),
        "status": run_git(repo_root, ["status", "--porcelain=v1"]),
        "remotes": run_git(repo_root, ["remote", "-v"]),
        "submodules": run_git(repo_root, ["submodule", "status", "--recursive"]),
    }
    return {
        "is_repository": probes["root"]["return_code"] == 0,
        "probes": probes,
    }


def collect_python_symbols(
    text: str, relative: str, destination: list[dict[str, Any]]
) -> None:
    if len(destination) >= MAX_RECORDS_PER_KIND:
        return
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not SYMBOL_HINT_RE.search(node.name):
            continue
        destination.append(
            {
                "name": node.name,
                "kind": "class" if isinstance(node, ast.ClassDef) else "function",
                "source_path": relative,
                "line": getattr(node, "lineno", None),
            }
        )
        if len(destination) >= MAX_RECORDS_PER_KIND:
            break


def build_search_queries(title: str, paper_id: str) -> list[str]:
    queries: list[str] = []
    if title:
        quoted = f'"{title}"'
        queries.extend(
            [
                f"{quoted} official code",
                f"{quoted} pretrained weights checkpoint",
                f"site:huggingface.co/models {quoted}",
                f"site:huggingface.co/datasets {quoted}",
                f"site:github.com {quoted} releases checkpoint",
            ]
        )
    if paper_id:
        queries.extend(
            [
                f'"{paper_id}" official code',
                f'"{paper_id}" Hugging Face model',
            ]
        )
    return queries


def scan_repository(
    repo_root: Path, max_files: int, max_file_bytes: int
) -> dict[str, Any]:
    scan: dict[str, Any] = {
        "visited_files": 0,
        "text_files_scanned": 0,
        "truncated": False,
        "skipped_large_or_binary": [],
        "unreadable": [],
    }
    dependency_files: list[str] = []
    config_files: list[str] = []
    documentation_files: list[str] = []
    local_weights: list[dict[str, Any]] = []
    weight_candidates: list[dict[str, Any]] = []
    model_hub_ids: list[dict[str, Any]] = []
    entry_commands: list[dict[str, Any]] = []
    paper_identifiers: list[dict[str, Any]] = []
    code_symbols: list[dict[str, Any]] = []
    metric_counts: Counter[str] = Counter()
    dataset_counts: Counter[str] = Counter()
    metric_evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)
    dataset_evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)

    weight_seen: set[tuple[Any, ...]] = set()
    model_seen: set[tuple[Any, ...]] = set()
    entry_seen: set[tuple[Any, ...]] = set()
    identifier_seen: set[tuple[Any, ...]] = set()

    for current_root, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = sorted(
            name for name in dirnames if name.lower() not in EXCLUDED_DIRS
        )
        for filename in sorted(filenames):
            path = Path(current_root) / filename
            scan["visited_files"] += 1
            if scan["visited_files"] > max_files:
                scan["truncated"] = True
                break
            relative = safe_relative(path, repo_root)
            lower_name = path.name.lower()

            if SECRET_FILE_RE.search(lower_name):
                scan["unreadable"].append(
                    {"source_path": relative, "reason": "credential-like filename"}
                )
                continue

            if path.suffix.lower() in WEIGHT_SUFFIXES:
                try:
                    size = path.stat().st_size
                except OSError:
                    size = None
                local_weights.append(
                    {
                        "source_path": relative,
                        "size_bytes": size,
                        "format": path.suffix.lower(),
                        "weight_type": weight_type_for(relative),
                        "official_status": "UNKNOWN",
                    }
                )

            if not is_text_candidate(path):
                continue
            text = read_text(path, max_file_bytes)
            if text is None:
                scan["skipped_large_or_binary"].append(relative)
                continue
            scan["text_files_scanned"] += 1

            rel_path = Path(relative)
            if is_dependency_file(rel_path):
                dependency_files.append(relative)
            if rel_path.suffix.lower() in {".yaml", ".yml", ".json", ".toml", ".cfg"}:
                config_files.append(relative)
            if lower_name.startswith(("readme", "license", "copying")) or (
                rel_path.suffix.lower() in {".md", ".rst"} and "docs/" in relative
            ):
                documentation_files.append(relative)

            if path.suffix.lower() == ".py":
                collect_python_symbols(text, relative, code_symbols)

            for line_no, raw_line in enumerate(text.splitlines(), start=1):
                line = raw_line.strip()
                lower = line.lower()
                if not line:
                    continue

                for match in ARXIV_RE.finditer(line):
                    value = match.group(1).rstrip(".pdf")
                    add_unique(
                        paper_identifiers,
                        identifier_seen,
                        ("arxiv", value),
                        {
                            "kind": "arxiv",
                            "value": value,
                            "source_path": relative,
                            "line": line_no,
                        },
                    )
                for match in DOI_RE.finditer(line):
                    value = match.group(0).rstrip(".,);")
                    add_unique(
                        paper_identifiers,
                        identifier_seen,
                        ("doi", value.lower()),
                        {
                            "kind": "doi",
                            "value": value,
                            "source_path": relative,
                            "line": line_no,
                        },
                    )

                entry_match = ENTRY_RE.match(line)
                if entry_match:
                    command = f"{entry_match.group(1)} {entry_match.group(2)}"
                    add_unique(
                        entry_commands,
                        entry_seen,
                        (relative, line_no, command),
                        {
                            "command": command[:1000],
                            "source_path": relative,
                            "line": line_no,
                        },
                    )

                for match in HF_CALL_RE.finditer(line):
                    model_id = match.group(1)
                    add_unique(
                        model_hub_ids,
                        model_seen,
                        ("huggingface", model_id),
                        {
                            "provider": "huggingface",
                            "repo_id": model_id,
                            "source_path": relative,
                            "line": line_no,
                            "official_status": "UNKNOWN",
                        },
                    )
                    add_unique(
                        weight_candidates,
                        weight_seen,
                        ("huggingface_id", model_id),
                        {
                            "kind": "model_hub_id",
                            "value": model_id,
                            "provider": "huggingface",
                            "weight_type": weight_type_for(line),
                            "source_path": relative,
                            "line": line_no,
                            "official_status": "UNKNOWN",
                            "access_status": "UNVERIFIED",
                        },
                    )

                for url_match in URL_RE.finditer(line):
                    url = sanitize_url(url_match.group(0))
                    hf_match = HF_URL_RE.match(url)
                    if hf_match:
                        model_id = hf_match.group(1)
                        add_unique(
                            model_hub_ids,
                            model_seen,
                            ("huggingface", model_id),
                            {
                                "provider": "huggingface",
                                "repo_id": model_id,
                                "url": url,
                                "source_path": relative,
                                "line": line_no,
                                "official_status": "UNKNOWN",
                            },
                        )
                    if WEIGHT_CONTEXT_RE.search(line) or provider_for(url) in {
                        "huggingface",
                        "github_release",
                        "google_drive",
                        "baidu_netdisk",
                        "dropbox",
                    }:
                        add_unique(
                            weight_candidates,
                            weight_seen,
                            ("url", url),
                            {
                                "kind": "url",
                                "value": url,
                                "provider": provider_for(url),
                                "weight_type": weight_type_for(line),
                                "source_path": relative,
                                "line": line_no,
                                "context": line[:1000],
                                "official_status": "UNKNOWN",
                                "access_status": "UNVERIFIED",
                            },
                        )

                for term in METRIC_TERMS:
                    if re.search(rf"(?<![A-Za-z0-9_]){re.escape(term)}(?![A-Za-z0-9_])", lower):
                        metric_counts[term] += 1
                        if len(metric_evidence[term]) < 5:
                            metric_evidence[term].append(
                                {"source_path": relative, "line": line_no}
                            )
                for term in DATASET_TERMS:
                    if re.search(rf"(?<![A-Za-z0-9_]){re.escape(term)}(?![A-Za-z0-9_])", lower):
                        dataset_counts[term] += 1
                        if len(dataset_evidence[term]) < 5:
                            dataset_evidence[term].append(
                                {"source_path": relative, "line": line_no}
                            )
            if scan["truncated"]:
                break
        if scan["truncated"]:
            break

    for local in local_weights:
        add_unique(
            weight_candidates,
            weight_seen,
            ("local", local["source_path"]),
            {
                "kind": "local_file",
                "value": f"local:{local['source_path']}",
                "provider": "local",
                "weight_type": local["weight_type"],
                "source_path": local["source_path"],
                "size_bytes": local["size_bytes"],
                "official_status": "UNKNOWN",
                "access_status": "LOCAL_PRESENT",
            },
        )

    return {
        "scan": scan,
        "project_files": {
            "dependency_files": sorted(set(dependency_files)),
            "config_files": sorted(set(config_files)),
            "documentation_files": sorted(set(documentation_files)),
        },
        "paper_identifiers": paper_identifiers,
        "entry_commands": entry_commands,
        "code_symbols": code_symbols,
        "model_hub_ids": model_hub_ids,
        "local_weight_files": local_weights,
        "weight_candidates": weight_candidates,
        "metric_mentions": [
            {
                "name": name,
                "count": count,
                "evidence": metric_evidence[name],
            }
            for name, count in metric_counts.most_common()
        ],
        "dataset_mentions": [
            {
                "name": name,
                "count": count,
                "evidence": dataset_evidence[name],
            }
            for name, count in dataset_counts.most_common()
        ],
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    output_dir = args.output_dir.resolve()
    if not repo_root.is_dir():
        print(f"Repository root does not exist: {repo_root}", file=sys.stderr)
        return 2
    if args.max_files <= 0 or args.max_file_bytes <= 0:
        print("Scan limits must be positive.", file=sys.stderr)
        return 2
    output_dir.mkdir(parents=True, exist_ok=True)

    collected = scan_repository(
        repo_root, args.max_files, args.max_file_bytes
    )
    generated_at = now_utc()
    project_evidence = {
        "schema_version": SCHEMA_VERSION,
        "script_version": SCRIPT_VERSION,
        "generated_at": generated_at,
        "repo_root": redact_home(str(repo_root)),
        "non_destructive": True,
        "network_used": False,
        "paper": {
            "title": args.paper_title or None,
            "identifier": args.paper_id or None,
        },
        "git": collect_git(repo_root),
        **{key: value for key, value in collected.items() if key != "weight_candidates"},
        "suggested_web_queries": build_search_queries(
            args.paper_title, args.paper_id
        ),
        "interpretation_required": True,
        "warnings": [
            "Repository references are candidates, not proof of paper-code alignment.",
            "Weight officialness and remote availability require web verification.",
            "No remote file or model weight was downloaded.",
        ],
    }
    weight_evidence = {
        "schema_version": SCHEMA_VERSION,
        "script_version": SCRIPT_VERSION,
        "generated_at": generated_at,
        "paper": project_evidence["paper"],
        "candidates": collected["weight_candidates"],
        "status_vocabulary": [
            "AVAILABLE_VERIFIED",
            "AVAILABLE_RESTRICTED",
            "ANNOUNCED_NOT_FOUND",
            "THIRD_PARTY_ONLY",
            "BROKEN_OR_REMOVED",
            "NOT_RELEASED",
            "UNKNOWN",
        ],
        "agent_reviewed": False,
        "interpretation_required": True,
    }

    project_path = output_dir / "project_evidence.json"
    weight_path = output_dir / "weight_evidence.json"
    write_json(project_path, project_evidence)
    write_json(weight_path, weight_evidence)
    summary = {
        "status": "ok",
        "project_evidence": redact_home(str(project_path)),
        "weight_evidence": redact_home(str(weight_path)),
        "text_files_scanned": collected["scan"]["text_files_scanned"],
        "weight_candidates": len(collected["weight_candidates"]),
        "model_hub_ids": len(collected["model_hub_ids"]),
        "entry_commands": len(collected["entry_commands"]),
        "scan_truncated": collected["scan"]["truncated"],
        "interpretation_required": True,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
