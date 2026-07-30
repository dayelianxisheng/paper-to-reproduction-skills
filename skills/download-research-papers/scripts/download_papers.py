#!/usr/bin/env python3
"""Download and validate research-paper PDFs from a JSON manifest."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


MIN_PDF_BYTES = 1024
PDF_SCAN_BYTES = 1024
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/124.0 Safari/537.36 "
    "ResearchPaperDownloader/1.0"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch-download PDFs, validate them, and write a JSON report."
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument(
        "--report",
        type=Path,
        help="Report path (default: <output>/download_report.json)",
    )
    return parser.parse_args()


def load_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, list) or not data:
        raise ValueError("Manifest must be a non-empty JSON array.")

    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Manifest item {index} must be an object.")
        title = str(item.get("title", "")).strip()
        filename = str(item.get("filename", "")).strip()
        url = str(item.get("url", "")).strip()
        if not filename or Path(filename).name != filename:
            raise ValueError(f"Item {index} has an unsafe filename: {filename!r}")
        if not filename.lower().endswith(".pdf"):
            raise ValueError(f"Item {index} filename must end in .pdf")
        if filename.casefold() in seen:
            raise ValueError(f"Duplicate filename: {filename}")
        if not url.lower().startswith(("https://", "http://")):
            raise ValueError(f"Item {index} needs an HTTP(S) URL.")
        seen.add(filename.casefold())
        result.append({"title": title or filename, "filename": filename, "url": url})
    return result


def valid_pdf(path: Path) -> bool:
    try:
        if path.stat().st_size < MIN_PDF_BYTES:
            return False
        with path.open("rb") as handle:
            return b"%PDF-" in handle.read(PDF_SCAN_BYTES)
    except OSError:
        return False


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def valid_result(item: dict[str, str], path: Path, status: str) -> dict[str, Any]:
    return {
        **item,
        "status": status,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def download_one(
    item: dict[str, str],
    output: Path,
    retries: int,
    timeout: float,
    print_lock: threading.Lock,
) -> dict[str, Any]:
    target = output / item["filename"]
    if valid_pdf(target):
        with print_lock:
            print(f"[skip] {item['filename']}", flush=True)
        return valid_result(item, target, "skipped")

    part = output / f".{item['filename']}.part"
    last_error = "unknown error"
    for attempt in range(1, retries + 1):
        try:
            request = urllib.request.Request(
                item["url"],
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.5",
                },
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                with part.open("wb") as handle:
                    while True:
                        block = response.read(1024 * 1024)
                        if not block:
                            break
                        handle.write(block)
            if not valid_pdf(part):
                content_type = response.headers.get("Content-Type", "unknown")
                raise ValueError(
                    f"response is not a valid PDF (Content-Type: {content_type})"
                )
            os.replace(part, target)
            with print_lock:
                print(f"[ok]   {item['filename']}", flush=True)
            return valid_result(item, target, "downloaded")
        except (
            OSError,
            TimeoutError,
            ValueError,
            urllib.error.HTTPError,
            urllib.error.URLError,
        ) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            try:
                part.unlink(missing_ok=True)
            except OSError:
                pass
            if attempt < retries:
                time.sleep(min(2 ** (attempt - 1), 8))

    with print_lock:
        print(f"[fail] {item['filename']}: {last_error}", flush=True)
    return {**item, "status": "failed", "error": last_error}


def main() -> int:
    args = parse_args()
    if args.workers < 1 or args.retries < 1 or args.timeout <= 0:
        raise ValueError("workers, retries, and timeout must be positive.")

    manifest = load_manifest(args.manifest.resolve())
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = (args.report or output / "download_report.json").resolve()
    print_lock = threading.Lock()

    results: list[dict[str, Any] | None] = [None] * len(manifest)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_indexes = {
            executor.submit(
                download_one,
                item,
                output,
                args.retries,
                args.timeout,
                print_lock,
            ): index
            for index, item in enumerate(manifest)
        }
        for future in concurrent.futures.as_completed(future_indexes):
            results[future_indexes[future]] = future.result()

    final_results = [result for result in results if result is not None]
    counts = {
        status: sum(result["status"] == status for result in final_results)
        for status in ("downloaded", "skipped", "failed")
    }
    report = {
        "manifest": str(args.manifest.resolve()),
        "output": str(output),
        "counts": counts,
        "results": final_results,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(
        f"Completed: {counts['downloaded']} downloaded, "
        f"{counts['skipped']} skipped, {counts['failed']} failed."
    )
    print(f"Report: {report_path}")
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"fatal: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
