#!/usr/bin/env python3
"""Invoke PDF2zh on native Linux with a narrow CLI fallback for /compare."""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request


DEFAULT_CONFIG = {
    "engine": "pdf2zh_next",
    "service": "bing",
    "next_service": "siliconflowfree",
    "sourceLang": "en",
    "targetLang": "zh-CN",
    "skipLastPages": "0",
    "threadNum": "4",
    "qps": "10",
    "poolSize": "0",
    "mono": "true",
    "dual": "true",
    "mono_cut": "false",
    "dual_cut": "false",
    "crop_compare": "false",
    "compare": "false",
    "babeldoc": "false",
    "skipSubsetFonts": "false",
    "fontFile": "",
    "fontFamily": "auto",
    "dualMode": "LR",
    "transFirst": "true",
    "ocr": "false",
    "autoOcr": "true",
    "noWatermark": "true",
    "saveGlossary": "false",
    "disableGlossary": "false",
    "noDual": "false",
    "noMono": "false",
    "skipClean": "false",
    "disableRichTextTranslate": "false",
    "enhanceCompatibility": "false",
    "translateTableText": "false",
    "onlyIncludeTranslatedPage": "false",
}


def existing_server_directory(explicit: str | None) -> Path:
    candidates = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    if os.environ.get("PDF2ZH_SERVER_DIRECTORY"):
        candidates.append(Path(os.environ["PDF2ZH_SERVER_DIRECTORY"]).expanduser())
    candidates.extend(
        [
            Path.home() / "resource/env/zotero/zotero-pdf2zh/server",
            Path.home() / "resource/env/fanyi/server/server",
        ]
    )
    for candidate in candidates:
        resolved = candidate.resolve()
        if (resolved / "server.py").is_file():
            return resolved
    raise FileNotFoundError("PDF2zh server directory not found; pass --server-directory")


def redact(text: str) -> str:
    substitutions = [
        (r"(?i)(api[_ -]?key|token|authorization|secret)(\s*[:=]\s*)\S+", r"\1\2[REDACTED]"),
        (r"(?i)bearer\s+\S+", "Bearer [REDACTED]"),
        (r"\bsk-[A-Za-z0-9_-]{8,}\b", "[REDACTED_KEY]"),
    ]
    for pattern, replacement in substitutions:
        text = re.sub(pattern, replacement, text)
    return text


def valid_pdf(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 5:
        return False
    with path.open("rb") as stream:
        return stream.read(5) == b"%PDF-"


def safe_output_paths(translated_directory: Path, file_names: list[str]) -> list[Path]:
    root = translated_directory.resolve()
    paths = []
    for file_name in file_names:
        if Path(file_name).name != file_name:
            raise ValueError(f"Unsafe output filename returned by PDF2zh: {file_name!r}")
        output = (root / file_name).resolve()
        if output.parent != root:
            raise ValueError(f"Output escaped translated directory: {output}")
        if not valid_pdf(output):
            raise ValueError(f"Output is missing or does not start with %PDF-: {output}")
        paths.append(output)
    return paths


def invoke_rest(args: argparse.Namespace, translated_directory: Path) -> tuple[list[Path], float]:
    config = dict(DEFAULT_CONFIG)
    config["next_service"] = args.next_service
    config["sourceLang"] = args.source_language
    config["targetLang"] = args.target_language
    payload = {
        "fileName": args.source.name,
        "fileContent": "data:application/pdf;base64,"
        + base64.b64encode(args.source.read_bytes()).decode("ascii"),
        **config,
    }
    request = urllib.request.Request(
        f"{args.server_url.rstrip('/')}/{args.endpoint}",
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=args.timeout_seconds) as response:
        result = json.load(response)
    elapsed = time.monotonic() - started
    if result.get("status") != "success" or not result.get("fileList"):
        raise RuntimeError("PDF2zh REST response did not contain a successful fileList")
    return safe_output_paths(translated_directory, list(result["fileList"])), elapsed


def direct_cli_fallback(
    args: argparse.Namespace, server_directory: Path, translated_directory: Path
) -> tuple[list[Path], list[Path], float]:
    if args.endpoint != "compare":
        raise RuntimeError("Direct CLI fallback is only defined for the compare endpoint")
    if args.next_service != "siliconflowfree":
        raise RuntimeError("Direct CLI fallback currently supports only siliconflowfree")
    executable = server_directory / "zotero-pdf2zh-next-venv/bin/pdf2zh_next"
    config_file = server_directory / "config/config.toml"
    if not executable.is_file():
        raise FileNotFoundError(f"pdf2zh_next executable not found: {executable}")
    if not config_file.is_file():
        raise FileNotFoundError(f"PDF2zh config file not found: {config_file}")
    translated_directory.mkdir(parents=True, exist_ok=True)
    command = [
        str(executable),
        str(args.source),
        "--siliconflowfree",
        "--qps",
        "10",
        "--output",
        str(translated_directory),
        "--lang-in",
        args.source_language,
        "--lang-out",
        args.target_language,
        "--config-file",
        str(config_file),
        "--watermark-output-mode",
        "no_watermark",
        "--no-mono",
        "--dual-translate-first",
        "--auto-enable-ocr-workaround",
        "--pool-max-worker",
        "100",
    ]
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=server_directory,
        capture_output=True,
        text=True,
        timeout=args.timeout_seconds,
        check=False,
    )
    elapsed = time.monotonic() - started
    if completed.returncode:
        combined = redact("\n".join([completed.stdout, completed.stderr]))
        tail = "\n".join(combined.splitlines()[-80:])
        raise RuntimeError(f"pdf2zh_next exited with {completed.returncode}:\n{tail}")

    expected_dual = (
        translated_directory
        / f"{args.source.stem}.no_watermark.{args.target_language}.dual.pdf"
    )
    if not valid_pdf(expected_dual):
        candidates = sorted(
            translated_directory.glob(f"{args.source.stem}*.dual.pdf"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        expected_dual = next((path for path in candidates if valid_pdf(path)), expected_dual)
    if not valid_pdf(expected_dual):
        raise RuntimeError("CLI completed but no valid dual PDF was found")

    compare_path = translated_directory / f"{args.source.stem}.compare.pdf"
    shutil.copy2(expected_dual, compare_path)
    if not valid_pdf(compare_path):
        raise RuntimeError(f"Failed to create a valid compare PDF: {compare_path}")
    return [compare_path.resolve()], [expected_dual.resolve()], elapsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--server-directory")
    parser.add_argument("--server-url", default="http://127.0.0.1:8890")
    parser.add_argument("--translated-directory", type=Path)
    parser.add_argument(
        "--endpoint", choices=("translate", "compare", "crop", "crop-compare"), default="compare"
    )
    parser.add_argument("--next-service", default="siliconflowfree")
    parser.add_argument("--source-language", default="en")
    parser.add_argument("--target-language", default="zh-CN")
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--no-cli-fallback", action="store_true")
    parser.add_argument("--force-cli", action="store_true")
    parser.add_argument("--delivery", type=Path)
    args = parser.parse_args()
    args.source = args.source.expanduser().resolve()
    if not valid_pdf(args.source):
        parser.error(f"source is missing, empty, or not a PDF: {args.source}")
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be positive")
    return args


def main() -> int:
    args = parse_args()
    server_directory = existing_server_directory(args.server_directory)
    translated_directory = (
        args.translated_directory.expanduser().resolve()
        if args.translated_directory
        else (server_directory / "translated").resolve()
    )
    translated_directory.mkdir(parents=True, exist_ok=True)
    method = "rest"
    fallback_reason = None
    preserved: list[Path] = []

    if args.force_cli:
        method = "cli-forced"
        outputs, preserved, elapsed = direct_cli_fallback(
            args, server_directory, translated_directory
        )
    else:
        try:
            outputs, elapsed = invoke_rest(args, translated_directory)
        except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError) as error:
            if args.no_cli_fallback:
                raise
            method = "cli-fallback"
            if isinstance(error, urllib.error.HTTPError):
                detail = error.read(8192).decode("utf-8", errors="replace")
                try:
                    payload = json.loads(detail)
                    fallback_reason = f"http-{error.code}:{payload.get('errorType', 'error')}"
                except json.JSONDecodeError:
                    fallback_reason = f"http-{error.code}"
            else:
                fallback_reason = error.__class__.__name__
            outputs, preserved, elapsed = direct_cli_fallback(
                args, server_directory, translated_directory
            )

    delivery = None
    if args.delivery:
        delivery = args.delivery.expanduser().resolve()
        delivery.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(outputs[0], delivery)
        if not valid_pdf(delivery):
            raise RuntimeError(f"Delivery copy is invalid: {delivery}")

    result = {
        "status": "success",
        "method": method,
        "fallbackReason": fallback_reason,
        "endpoint": args.endpoint,
        "source": str(args.source),
        "elapsedSeconds": round(elapsed, 1),
        "outputFiles": [
            {"path": str(path), "bytes": path.stat().st_size, "pdfHeaderValid": True}
            for path in outputs
        ],
        "preservedFiles": [str(path) for path in preserved],
        "delivery": str(delivery) if delivery else None,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {redact(str(error))}", file=sys.stderr)
        raise SystemExit(1)
