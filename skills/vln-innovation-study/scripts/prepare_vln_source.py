#!/usr/bin/env python3
"""Prepare an auditable source bundle for one VLN paper PDF."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
READING_AID_PATTERN = re.compile(
    r"(^|[._\-\s])(compare|dual|bilingual|translated|translation|chinese|zh|zh-cn)"
    r"($|[._\-\s])|双语|对照|译文|翻译",
    re.IGNORECASE,
)
SECTION_TITLES = {
    "abstract",
    "introduction",
    "related work",
    "background",
    "method",
    "methods",
    "approach",
    "experiments",
    "experimental results",
    "results",
    "discussion",
    "limitations",
    "conclusion",
    "conclusions",
    "references",
    "摘要",
    "引言",
    "相关工作",
    "方法",
    "实验",
    "结果",
    "讨论",
    "局限",
    "结论",
    "参考文献",
}


class SourcePreparationError(RuntimeError):
    """Raised when a safe anchor source cannot be selected or prepared."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_reading_aid(path: Path) -> bool:
    return bool(READING_AID_PATTERN.search(path.stem))


def validate_pdf(path: Path) -> None:
    if not path.is_file():
        raise SourcePreparationError(f"PDF does not exist: {path}")
    if path.suffix.lower() != ".pdf":
        raise SourcePreparationError(f"Source is not a .pdf file: {path}")
    with path.open("rb") as handle:
        if handle.read(5) != b"%PDF-":
            raise SourcePreparationError(f"Invalid PDF header: {path}")


def inspect_candidates(paths: Iterable[Path]) -> list[dict[str, Any]]:
    """Validate, hash, and collapse byte-identical candidate PDFs."""
    by_hash: dict[str, dict[str, Any]] = {}
    for raw_path in paths:
        path = raw_path.expanduser().resolve()
        validate_pdf(path)
        digest = sha256_file(path)
        role = "reading-aid" if is_reading_aid(path) else "original-candidate"
        if digest in by_hash:
            existing = by_hash[digest]
            if role == "original-candidate" and existing["role"] == "reading-aid":
                previous_primary = existing["path"]
                existing["path"] = str(path)
                existing["role"] = role
                existing["duplicate_paths"].append(previous_primary)
            else:
                existing["duplicate_paths"].append(str(path))
            continue
        by_hash[digest] = {
            "path": str(path),
            "sha256": digest,
            "size_bytes": path.stat().st_size,
            "role": role,
            "duplicate_paths": [],
        }
    if not by_hash:
        raise SourcePreparationError("At least one --pdf candidate is required.")
    return list(by_hash.values())


def choose_anchor(
    candidates: list[dict[str, Any]], explicit_anchor: Path | None = None
) -> dict[str, Any]:
    if explicit_anchor is not None:
        anchor = str(explicit_anchor.expanduser().resolve())
        for candidate in candidates:
            if anchor == candidate["path"] or anchor in candidate["duplicate_paths"]:
                return candidate
        raise SourcePreparationError("--anchor must match one of the --pdf candidates.")

    originals = [
        candidate for candidate in candidates if candidate["role"] == "original-candidate"
    ]
    if len(originals) == 1:
        return originals[0]
    if len(originals) > 1:
        paths = "\n".join(f"- {candidate['path']}" for candidate in originals)
        raise SourcePreparationError(
            "Multiple distinct original PDF candidates remain. "
            "Inspect them and pass --anchor explicitly:\n" + paths
        )
    if len(candidates) == 1:
        return candidates[0]
    paths = "\n".join(f"- {candidate['path']}" for candidate in candidates)
    raise SourcePreparationError(
        "Only multiple transformed reading aids were found. "
        "Provide the original PDF or pass --anchor explicitly:\n" + paths
    )


def _run(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def page_count_from_pdfinfo(path: Path) -> tuple[int | None, str | None]:
    executable = shutil.which("pdfinfo")
    if executable is None:
        return None, "pdfinfo is unavailable"
    result = _run([executable, str(path)], timeout=30)
    if result.returncode != 0:
        return None, f"pdfinfo failed: {result.stderr.strip()}"
    match = re.search(r"^Pages:\s+(\d+)\s*$", result.stdout, re.MULTILINE)
    if not match:
        return None, "pdfinfo did not report a page count"
    return int(match.group(1)), None


def extract_with_poppler(path: Path) -> tuple[list[str], str | None]:
    executable = shutil.which("pdftotext")
    if executable is None:
        return [], "pdftotext is unavailable"
    result = _run(
        [executable, "-layout", "-enc", "UTF-8", str(path), "-"],
        timeout=120,
    )
    if result.returncode != 0:
        return [], f"pdftotext failed: {result.stderr.strip()}"
    pages = result.stdout.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    return [page.rstrip() for page in pages], None


def extract_with_pymupdf(path: Path) -> tuple[list[str], int | None, str | None]:
    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError:
        return [], None, "PyMuPDF is unavailable"
    try:
        document = fitz.open(path)
        pages = [page.get_text("text").rstrip() for page in document]
        page_count = document.page_count
        document.close()
        return pages, page_count, None
    except Exception as exc:  # pragma: no cover - library-specific failures
        return [], None, f"PyMuPDF failed: {exc}"


def extract_pages(path: Path) -> tuple[list[str], int | None, list[str], str]:
    warnings: list[str] = []
    page_count, count_warning = page_count_from_pdfinfo(path)
    if count_warning:
        warnings.append(count_warning)

    pages, text_warning = extract_with_poppler(path)
    extractor = "pdftotext"
    if text_warning:
        warnings.append(text_warning)
    if not pages:
        pages, fitz_count, fitz_warning = extract_with_pymupdf(path)
        extractor = "pymupdf"
        if page_count is None:
            page_count = fitz_count
        if fitz_warning:
            warnings.append(fitz_warning)
    return pages, page_count, warnings, extractor


def normalize_pages(pages: list[str], page_count: int | None) -> list[str]:
    if page_count is None:
        return pages
    if len(pages) < page_count:
        return pages + [""] * (page_count - len(pages))
    if len(pages) > page_count:
        return pages[:page_count]
    return pages


def _deduplicate_inventory(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, int]] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        key = (item["label"].casefold(), item["pdf_page"])
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def build_inventory(pages: list[str]) -> dict[str, list[dict[str, Any]]]:
    sections: list[dict[str, Any]] = []
    figures: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    equations: list[dict[str, Any]] = []

    numbered_heading = re.compile(r"^\s*(\d+(?:\.\d+)*)[.\s]+(.{2,100})\s*$")
    figure_pattern = re.compile(r"\b(?:Fig(?:ure)?\.?)\s*(\d+[A-Za-z]?)", re.I)
    table_pattern = re.compile(r"\bTable\s+([A-Z]?\d+[A-Za-z]?)", re.I)
    equation_pattern = re.compile(r"\((\d{1,3})\)\s*$")

    for pdf_page, page in enumerate(pages, start=1):
        for raw_line in page.splitlines():
            line = " ".join(raw_line.split())
            if not line:
                continue
            heading_match = numbered_heading.match(line)
            if heading_match:
                sections.append(
                    {
                        "label": f"{heading_match.group(1)} {heading_match.group(2)}",
                        "pdf_page": pdf_page,
                    }
                )
            elif line.casefold().rstrip(":") in SECTION_TITLES:
                sections.append({"label": line.rstrip(":"), "pdf_page": pdf_page})

            for match in figure_pattern.finditer(line):
                figures.append(
                    {"label": f"Figure {match.group(1)}", "pdf_page": pdf_page}
                )
            for match in table_pattern.finditer(line):
                tables.append(
                    {"label": f"Table {match.group(1)}", "pdf_page": pdf_page}
                )
            equation_match = equation_pattern.search(line)
            if equation_match:
                equations.append(
                    {
                        "label": f"Equation {equation_match.group(1)}",
                        "pdf_page": pdf_page,
                    }
                )

    return {
        "sections": _deduplicate_inventory(sections)[:250],
        "figures": _deduplicate_inventory(figures)[:250],
        "tables": _deduplicate_inventory(tables)[:250],
        "equations": _deduplicate_inventory(equations)[:500],
    }


def determine_locator_mode(
    selected: dict[str, Any],
    pages: list[str],
    page_count: int | None,
    force_source_limited: bool,
) -> tuple[str, list[str]]:
    warnings: list[str] = []
    text_characters = sum(len(page.strip()) for page in pages)
    boundaries_reliable = page_count is not None and len(pages) == page_count

    if force_source_limited or text_characters < 200:
        return "source-limited", [
            "The source contains insufficient extractable text; unseen details and locators "
            "must not be inferred."
        ]
    if selected["role"] == "reading-aid":
        warnings.append(
            "The selected source appears to be a bilingual or translated reading aid; "
            "its PDF page indices are not authoritative."
        )
        return "structure-grounded", warnings
    if boundaries_reliable:
        return "page-grounded", warnings
    warnings.append(
        "Extracted text is usable, but page boundaries do not match a verified page count."
    )
    return "structure-grounded", warnings


def default_cache_root() -> Path:
    configured = os.environ.get("XDG_CACHE_HOME")
    if configured:
        return Path(configured).expanduser() / "vln-innovation-study"
    return Path.home() / ".cache" / "vln-innovation-study"


def prepare_bundle(
    pdf_paths: list[Path],
    explicit_anchor: Path | None = None,
    output_dir: Path | None = None,
    force_source_limited: bool = False,
) -> tuple[dict[str, Any], Path]:
    candidates = inspect_candidates(pdf_paths)
    selected = choose_anchor(candidates, explicit_anchor)
    selected_path = Path(selected["path"])
    pages, page_count, extraction_warnings, extractor = extract_pages(selected_path)
    locator_mode, locator_warnings = determine_locator_mode(
        selected, pages, page_count, force_source_limited
    )
    pages = normalize_pages(pages, page_count)

    target_dir = (
        output_dir.expanduser().resolve()
        if output_dir
        else default_cache_root() / selected["sha256"]
    )
    target_dir.mkdir(parents=True, exist_ok=True)
    text_path = target_dir / "paper.txt"
    text_path.write_text("\f".join(pages), encoding="utf-8")

    bundle: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "locator_mode": locator_mode,
        "warnings": extraction_warnings + locator_warnings,
        "selected_source": {
            **selected,
            "page_count": page_count,
            "extractor": extractor,
        },
        "candidates": candidates,
        "text_artifact": str(text_path),
        "pages": [
            {"pdf_page": index, "characters": len(page.strip())}
            for index, page in enumerate(pages, start=1)
        ],
        "inventory": build_inventory(pages),
    }
    bundle_path = target_dir / "source_bundle.json"
    bundle_path.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return bundle, bundle_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare an auditable source bundle for one VLN paper."
    )
    parser.add_argument(
        "--pdf",
        action="append",
        required=True,
        type=Path,
        help="Candidate PDF path. Repeat for duplicate/original candidates.",
    )
    parser.add_argument(
        "--anchor",
        type=Path,
        help="Explicit anchor when multiple distinct originals remain.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory. Defaults to the user cache keyed by PDF SHA-256.",
    )
    parser.add_argument(
        "--source-limited",
        action="store_true",
        help="Force source-limited mode for partial or otherwise incomplete material.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        bundle, bundle_path = prepare_bundle(
            pdf_paths=args.pdf,
            explicit_anchor=args.anchor,
            output_dir=args.output_dir,
            force_source_limited=args.source_limited,
        )
    except (SourcePreparationError, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "source_bundle": str(bundle_path),
                "locator_mode": bundle["locator_mode"],
                "selected_source": bundle["selected_source"]["path"],
                "warnings": bundle["warnings"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
