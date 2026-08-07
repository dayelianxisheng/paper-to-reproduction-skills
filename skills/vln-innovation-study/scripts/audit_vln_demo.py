#!/usr/bin/env python3
"""Audit a VLN causal mechanism demo without claiming paper reproduction."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


VISUAL_SUFFIXES = {".png", ".svg", ".pdf", ".gif", ".tif", ".tiff"}
SOURCE_SUFFIXES = {".py", ".js", ".ts", ".cpp", ".cc", ".cxx", ".rs"}


def finding(severity: str, code: str, message: str) -> dict[str, str]:
    return {"severity": severity, "code": code, "message": message}


def contains(text: str, *patterns: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def audit_demo(demo_dir: Path) -> dict[str, Any]:
    root = demo_dir.expanduser().resolve()
    findings: list[dict[str, str]] = []
    readme = root / "README.md"
    outputs = root / "outputs"

    if not root.is_dir():
        findings.append(finding("error", "missing-demo", f"Demo directory not found: {root}"))
        readme_text = ""
    elif not readme.is_file():
        findings.append(finding("error", "missing-readme", "Demo must include README.md."))
        readme_text = ""
    else:
        readme_text = readme.read_text(encoding="utf-8")

    level_patterns = (
        ("Mechanism Demo", r"mechanism\s+demo|机制演示"),
        ("Minimum Experiment", r"minimum\s+experiment|最小实验"),
        (
            "Paper Reproduction",
            r"(?im)^(?:#{1,6}\s*)?(?:实验级别\s*[:：]\s*)?"
            r"(?:\*\*)?(?:paper\s+reproduction|论文复现)",
        ),
    )
    level_matches = [
        label for label, pattern in level_patterns if contains(readme_text, pattern)
    ]
    if len(level_matches) != 1:
        findings.append(
            finding(
                "error",
                "experiment-level",
                "README must identify exactly one level: Mechanism Demo, Minimum Experiment, or Paper Reproduction.",
            )
        )

    readme_checks = [
        (
            "missing-baseline-failure",
            "Describe the baseline failure.",
            (r"baseline", r"基线", r"前序.*失败", r"failure", r"因果对照"),
        ),
        (
            "missing-controls",
            "State controlled variables and the single intervention.",
            (
                r"控制变量",
                r"只改变",
                r"controlled",
                r"intervention",
                r"同一",
                r"相同",
                r"核心变量",
            ),
        ),
        (
            "missing-run-command",
            "Provide an exact run command.",
            (r"python(?:3)?\s+\S+\.py", r"运行命令"),
        ),
        (
            "missing-supported-claim",
            "State what the demo supports or proves.",
            (r"证明(?:了)?什么", r"支持.*结论", r"what.*(?:proves|supports)"),
        ),
        (
            "missing-non-claim",
            "State what the demo does not prove.",
            (r"不证明", r"不能.*说明", r"does\s+not\s+prove", r"non-claim"),
        ),
        (
            "missing-reproduction-boundary",
            "State how the demo differs from paper reproduction.",
            (r"复现", r"paper\s+reproduction", r"reproduction"),
        ),
    ]
    for code, message, patterns in readme_checks:
        if not contains(readme_text, *patterns):
            findings.append(finding("error", code, message))

    source_files = (
        [
            path
            for path in root.rglob("*")
            if path.is_file()
            and path.suffix.lower() in SOURCE_SUFFIXES
            and "outputs" not in path.parts
        ]
        if root.is_dir()
        else []
    )
    if not source_files:
        findings.append(finding("error", "missing-source", "Demo has no executable source file."))
        source_text = ""
    else:
        source_text = "\n".join(
            path.read_text(encoding="utf-8", errors="replace") for path in source_files
        )
    if source_text and not contains(
        source_text,
        r"\bseed\b",
        r"default_rng",
        r"random_state",
        r"manual_seed",
    ):
        findings.append(
            finding(
                "error",
                "missing-deterministic-seed",
                "Expose or fix deterministic random seeds in demo source.",
            )
        )

    visual_files = (
        [
            path
            for path in outputs.rglob("*")
            if path.is_file() and path.suffix.lower() in VISUAL_SUFFIXES
        ]
        if outputs.is_dir()
        else []
    )
    if not visual_files:
        findings.append(
            finding("error", "missing-visual-output", "Generate at least one visual artifact.")
        )

    metrics_files = list(outputs.rglob("*.json")) if outputs.is_dir() else []
    if not metrics_files:
        findings.append(
            finding(
                "error",
                "missing-metrics",
                "Save at least one machine-readable JSON metrics artifact.",
            )
        )
    for metrics_path in metrics_files:
        try:
            json.loads(metrics_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            findings.append(
                finding(
                    "error",
                    "invalid-metrics-json",
                    f"Invalid metrics JSON {metrics_path.name}: {exc}",
                )
            )

    if source_text and contains(source_text, r"matplotlib", r"seaborn", r"plt\.") and not re.search(
        r"[\u3400-\u9fff]", source_text
    ):
        findings.append(
            finding(
                "warning",
                "non-chinese-visual-labels",
                "No Chinese text was detected in plotting source; verify titles, labels, legends, and annotations.",
            )
        )

    errors = sum(item["severity"] == "error" for item in findings)
    warnings = sum(item["severity"] == "warning" for item in findings)
    return {
        "demo": str(root),
        "experiment_level": level_matches[0] if len(level_matches) == 1 else None,
        "passed": errors == 0,
        "error_count": errors,
        "warning_count": warnings,
        "visual_artifacts": [str(path) for path in visual_files],
        "metrics_artifacts": [str(path) for path in metrics_files],
        "findings": findings,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit a VLN mechanism demo.")
    parser.add_argument("demo_directory", type=Path)
    parser.add_argument("--json-output", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = audit_demo(args.demo_directory)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
