#!/usr/bin/env python3
"""Audit VLN working analyses and concise user path notes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


PAGE_ANCHOR = re.compile(
    r"(?<![\w.])(?:p(?:age)?\.?\s*\d+|第\s*\d+\s*页)", re.IGNORECASE
)
STRUCTURAL_ANCHOR = re.compile(
    r"\b(?:Table|Fig(?:ure)?|Eq(?:uation)?)\.?\s*[A-Z]?\d+|"
    r"(?:表|图|公式)\s*[A-Z]?\d+|§\s*\d+",
    re.IGNORECASE,
)
NUMERIC_RESULT = re.compile(
    r"(?:\d+(?:\.\d+)?\s*%|\b0\.\d+\b|"
    r"\d+(?:\.\d+)?\s*(?:points?|秒|步|米|m|GB|MB|ms)\b)",
    re.IGNORECASE,
)
PROVENANCE = re.compile(
    r"\b(?:AUTHOR|LITERATURE|INFERENCE|HYPOTHESIS|USER)\b"
)


def finding(severity: str, code: str, message: str) -> dict[str, str]:
    return {"severity": severity, "code": code, "message": message}


def contains(text: str, *patterns: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def load_locator_mode(source_bundle: Path | None) -> str | None:
    if source_bundle is None:
        return None
    try:
        data = json.loads(source_bundle.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read source bundle: {exc}") from exc
    mode = data.get("locator_mode")
    if mode not in {"page-grounded", "structure-grounded", "source-limited"}:
        raise ValueError(f"Invalid locator_mode in source bundle: {mode!r}")
    return mode


def audit_locator_safety(
    text: str,
    locator_mode: str | None,
    verified_page_anchors: bool = False,
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    unsafe_structure_pages = (
        locator_mode == "structure-grounded" and not verified_page_anchors
    )
    if (
        unsafe_structure_pages or locator_mode == "source-limited"
    ) and PAGE_ANCHOR.search(text):
        findings.append(
            finding(
                "error",
                "unsafe-page-anchor",
                f"{locator_mode} material must not use unverified PDF page anchors.",
            )
        )
    if locator_mode == "source-limited" and STRUCTURAL_ANCHOR.search(text):
        findings.append(
            finding(
                "error",
                "unseen-structural-anchor",
                "Source-limited material must not claim unseen table, figure, or equation anchors.",
            )
        )
    return findings


def audit_working_analysis(
    text: str,
    locator_mode: str | None,
    verified_page_anchors: bool = False,
) -> list[dict[str, str]]:
    findings = audit_locator_safety(text, locator_mode, verified_page_anchors)

    primary_count = len(
        re.findall(r"主创新层|primary\s+innovation\s+layer", text, re.IGNORECASE)
    )
    if primary_count != 1:
        findings.append(
            finding(
                "error",
                "primary-innovation-count",
                f"Working analysis must name exactly one primary innovation layer; found {primary_count}.",
            )
        )

    secondary_count = len(
        re.findall(
            r"支撑创新层|次要创新层|secondary\s+innovation\s+layer",
            text,
            re.IGNORECASE,
        )
    )
    if secondary_count > 2:
        findings.append(
            finding(
                "error",
                "secondary-innovation-count",
                f"At most two secondary innovation layers are allowed; found {secondary_count}.",
            )
        )

    required_checks = [
        (
            "missing-predecessor",
            "Name the closest predecessor or previous paradigm.",
            (r"前序", r"前人做法", r"最近.*前身", r"closest\s+predecessor", r"previous\s+paradigm"),
        ),
        (
            "missing-training-inference-boundary",
            "State both the training and inference boundaries.",
            (r"训练", r"training"),
        ),
        (
            "missing-inference-boundary",
            "State inference-time information and behavior.",
            (r"推理", r"inference"),
        ),
        (
            "missing-dependency-boundary",
            "Record dependencies, cost, limitations, or deployment boundaries.",
            (r"依赖", r"成本", r"边界", r"局限", r"dependency", r"cost", r"limitation", r"latency", r"memory"),
        ),
        (
            "missing-demo-suitability",
            "Assign demo suitability as HIGH, MEDIUM, or LOW.",
            (r"demo.{0,20}\b(?:HIGH|MEDIUM|LOW)\b", r"演示适合度.{0,20}\b(?:HIGH|MEDIUM|LOW)\b"),
        ),
        (
            "missing-historical-position",
            "Add a one-sentence historical position.",
            (r"一句话历史位置", r"historical\s+position"),
        ),
    ]
    for code, message, patterns in required_checks:
        if not contains(text, *patterns):
            findings.append(finding("error", code, message))

    if not STRUCTURAL_ANCHOR.search(text):
        findings.append(
            finding(
                "error",
                "missing-evidence-anchor",
                "Anchor the strongest causal evidence to a table, figure, equation, or section.",
            )
        )
    if not NUMERIC_RESULT.search(text):
        findings.append(
            finding(
                "error",
                "missing-numeric-result",
                "Record the strongest available quantitative result or explicitly state that none is available.",
            )
        )
    if not contains(text, r"\bMUST-DERIVE\b", r"\bUNDERSTAND-ROLE\b", r"\bSKIP\b"):
        findings.append(
            finding(
                "error",
                "missing-equation-classification",
                "Classify relevant equations as MUST-DERIVE, UNDERSTAND-ROLE, or SKIP.",
            )
        )
    if not PROVENANCE.search(text):
        findings.append(
            finding(
                "error",
                "missing-provenance",
                "Use at least one AUTHOR, LITERATURE, INFERENCE, HYPOTHESIS, or USER label.",
            )
        )
    if contains(text, r"证明", r"\bproves?\b", r"\bcauses?\b", r"导致") and not contains(
        text, r"受控", r"消融", r"controlled", r"ablation", r"randomi[sz]ed"
    ):
        findings.append(
            finding(
                "warning",
                "causal-language-risk",
                "Strong causal language appears without an explicit controlled design or ablation.",
            )
        )
    return findings


def split_paper_blocks(text: str) -> list[str]:
    starts = list(
        re.finditer(
            r"(?m)^##\s+(?:第[一二三四五六七八九十\d]+篇|Paper\b)",
            text,
            re.IGNORECASE,
        )
    )
    if not starts:
        return [text]
    blocks: list[str] = []
    for index, start in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        blocks.append(text[start.start() : end])
    return blocks


def empty_headings(text: str) -> list[str]:
    lines = text.splitlines()
    empty: list[str] = []
    for index, line in enumerate(lines):
        heading_match = re.match(r"^(#{1,6})\s+\S", line)
        if not heading_match:
            continue
        level = len(heading_match.group(1))
        cursor = index + 1
        while cursor < len(lines) and not lines[cursor].strip():
            cursor += 1
        next_heading = (
            re.match(r"^(#{1,6})\s+\S", lines[cursor])
            if cursor < len(lines)
            else None
        )
        if cursor >= len(lines) or (
            next_heading and len(next_heading.group(1)) <= level
        ):
            empty.append(line.strip())
    return empty


def audit_path_note(
    text: str,
    locator_mode: str | None,
    verified_page_anchors: bool = False,
) -> list[dict[str, str]]:
    findings = audit_locator_safety(text, locator_mode, verified_page_anchors)
    if text.startswith("---\n"):
        findings.append(
            finding(
                "error",
                "yaml-frontmatter",
                "User path notes must not contain YAML frontmatter.",
            )
        )
    if re.search(r"(?im)^#\s*(?:论文索引|paper\s+index|创新地图|innovation\s+map)\s*$", text):
        findings.append(
            finding(
                "error",
                "agent-oriented-note",
                "notes/ must contain a learning path, not a paper index or innovation map.",
            )
        )
    if contains(text, r"\bTODO\b", r"\bTBD\b", r"待补充", r"placeholder"):
        findings.append(
            finding(
                "error",
                "placeholder-content",
                "Remove placeholders from the user path note.",
            )
        )
    for heading in empty_headings(text):
        findings.append(
            finding(
                "error",
                "empty-heading",
                f"Remove or fill empty heading: {heading}",
            )
        )

    for block_index, block in enumerate(split_paper_blocks(text), start=1):
        innovation_points = len(
            re.findall(r"(?m)^###\s+创新点\s*\d+", block, re.IGNORECASE)
        )
        if innovation_points > 3:
            findings.append(
                finding(
                    "warning",
                    "too-many-innovation-points",
                    f"Paper block {block_index} contains {innovation_points} innovation points; "
                    "consider retaining only the most useful three.",
                )
            )
        if contains(block, r"创新定位") and not contains(
            block, r"一句话历史位置", r"historical\s+position"
        ):
            findings.append(
                finding(
                    "warning",
                    "missing-path-position",
                    f"Paper block {block_index} has an innovation position but no one-sentence historical position.",
                )
            )
    return findings


def build_report(
    note_path: Path,
    profile: str,
    locator_mode: str | None,
    verified_page_anchors: bool,
    findings: list[dict[str, str]],
) -> dict[str, Any]:
    errors = sum(item["severity"] == "error" for item in findings)
    warnings = sum(item["severity"] == "warning" for item in findings)
    return {
        "note": str(note_path.resolve()),
        "profile": profile,
        "locator_mode": locator_mode,
        "verified_page_anchors": verified_page_anchors,
        "passed": errors == 0,
        "error_count": errors,
        "warning_count": warnings,
        "findings": findings,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit a VLN analysis or path note.")
    parser.add_argument("note", type=Path)
    parser.add_argument(
        "--profile",
        required=True,
        choices=("working-analysis", "path-note"),
    )
    parser.add_argument("--source-bundle", type=Path)
    parser.add_argument(
        "--verified-page-anchors",
        action="store_true",
        help="Allow page anchors in structure-grounded material only after visual verification.",
    )
    parser.add_argument("--json-output", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        text = args.note.read_text(encoding="utf-8")
        locator_mode = load_locator_mode(args.source_bundle)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.profile == "working-analysis":
        findings = audit_working_analysis(
            text, locator_mode, args.verified_page_anchors
        )
    else:
        findings = audit_path_note(text, locator_mode, args.verified_page_anchors)
    report = build_report(
        args.note,
        args.profile,
        locator_mode,
        args.verified_page_anchors,
        findings,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
