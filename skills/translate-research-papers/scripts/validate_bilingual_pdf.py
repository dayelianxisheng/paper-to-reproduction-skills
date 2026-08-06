#!/usr/bin/env python3
"""Validate a Linux PDF2zh output using Poppler command-line tools."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys


def require_command(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"required command is missing: {name}")


def valid_header(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 5:
        return False
    with path.open("rb") as stream:
        return stream.read(5) == b"%PDF-"


def pdf_info(path: Path) -> dict[str, object]:
    completed = subprocess.run(
        ["pdfinfo", str(path)], capture_output=True, text=True, check=True
    )
    pages_match = re.search(r"^Pages:\s+(\d+)$", completed.stdout, re.MULTILINE)
    size_match = re.search(
        r"^Page size:\s+([0-9.]+) x ([0-9.]+) pts", completed.stdout, re.MULTILINE
    )
    if not pages_match or not size_match:
        raise RuntimeError(f"could not parse pdfinfo output for {path}")
    return {
        "pages": int(pages_match.group(1)),
        "width": float(size_match.group(1)),
        "height": float(size_match.group(2)),
        "bytes": path.stat().st_size,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--translated", required=True, type=Path)
    parser.add_argument("--min-chinese-characters", type=int, default=100)
    parser.add_argument("--layout", choices=("any", "lr"), default="lr")
    parser.add_argument("--render-prefix", type=Path)
    args = parser.parse_args()
    args.source = args.source.expanduser().resolve()
    args.translated = args.translated.expanduser().resolve()
    if args.min_chinese_characters < 1:
        parser.error("--min-chinese-characters must be positive")
    return args


def main() -> int:
    args = parse_args()
    for command in ("pdfinfo", "pdftotext"):
        require_command(command)
    if not valid_header(args.source):
        raise RuntimeError(f"source does not start with %PDF-: {args.source}")
    if not valid_header(args.translated):
        raise RuntimeError(f"translated output does not start with %PDF-: {args.translated}")

    source_info = pdf_info(args.source)
    translated_info = pdf_info(args.translated)
    if source_info["pages"] != translated_info["pages"]:
        raise RuntimeError(
            f"page count mismatch: source={source_info['pages']} translated={translated_info['pages']}"
        )
    if args.layout == "lr":
        width_ratio = translated_info["width"] / source_info["width"]
        height_ratio = translated_info["height"] / source_info["height"]
        if width_ratio < 1.8 or not 0.9 <= height_ratio <= 1.1:
            raise RuntimeError(
                f"unexpected LR page geometry: width_ratio={width_ratio:.3f} "
                f"height_ratio={height_ratio:.3f}"
            )

    extracted = subprocess.run(
        ["pdftotext", "-enc", "UTF-8", str(args.translated), "-"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    chinese_characters = len(re.findall(r"[\u4e00-\u9fff]", extracted))
    nonempty_lines = sum(bool(line.strip()) for line in extracted.splitlines())
    if chinese_characters < args.min_chinese_characters:
        raise RuntimeError(
            f"meaningful Chinese text was not found: {chinese_characters} characters"
        )

    preview = None
    if args.render_prefix:
        require_command("pdftoppm")
        prefix = args.render_prefix.expanduser().resolve()
        prefix.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "pdftoppm",
                "-f",
                "1",
                "-singlefile",
                "-png",
                "-r",
                "110",
                str(args.translated),
                str(prefix),
            ],
            check=True,
        )
        preview = prefix.with_suffix(".png")
        if not preview.is_file():
            raise RuntimeError(f"preview was not created: {preview}")

    result = {
        "status": "valid",
        "source": {"path": str(args.source), **source_info},
        "translated": {"path": str(args.translated), **translated_info},
        "chineseCharacters": chinese_characters,
        "nonemptyTextLines": nonempty_lines,
        "preview": str(preview) if preview else None,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
