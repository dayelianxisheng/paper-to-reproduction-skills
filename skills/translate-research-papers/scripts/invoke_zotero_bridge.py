#!/usr/bin/env python3
"""Call the restricted PDF2zh Zotero bridge without exposing its token."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request


def default_token_path() -> Path:
    configured = os.environ.get("PDF2ZH_BRIDGE_TOKEN_PATH")
    if configured:
        return Path(configured).expanduser()
    if os.name == "nt":
        return Path(r"D:\software\Professional\Zotero\note\pdf2zh-bridge.token")
    return Path.home() / "Zotero/pdf2zh-bridge.token"


def read_token(path: Path) -> str:
    token = path.expanduser().read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"[A-Za-z0-9]{48,128}", token):
        raise ValueError(f"Bridge token file is invalid: {path}")
    return token


def creators(value: str | None) -> list[dict[str, str]] | None:
    if not value:
        return None
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        raise ValueError("--creators-json must be a JSON array")
    return parsed


def metadata_from_args(args: argparse.Namespace) -> dict[str, object]:
    metadata: dict[str, object] = {}
    for field in (
        "title",
        "shortTitle",
        "date",
        "DOI",
        "proceedingsTitle",
        "url",
        "pages",
        "language",
        "abstractNote",
    ):
        value = getattr(args, field, None)
        if value:
            metadata[field] = value
    parsed_creators = creators(getattr(args, "creators_json", None))
    if parsed_creators is not None:
        metadata["creators"] = parsed_creators
    return metadata


def request_bridge(args: argparse.Namespace, token: str) -> dict[str, object]:
    endpoint = args.action
    body = None
    method = "GET"
    if args.action == "prepare":
        method = "POST"
        body = {
            "sourcePath": str(args.source_path.expanduser().resolve()),
            "targetCollectionID": args.target_collection_id,
            "shortTitle": args.short_title,
        }
    elif args.action == "archive":
        method = "POST"
        body = {
            "sourceAttachmentID": args.source_attachment_id,
            "targetCollectionID": args.target_collection_id,
            "translatedPath": str(args.translated_path.expanduser().resolve()),
            "shortTitle": args.short_title,
            "service": args.service,
            "itemType": args.item_type,
            "metadata": metadata_from_args(args),
        }
        if args.template_item_id:
            body["templateItemID"] = args.template_item_id
    elif args.action == "github":
        method = "POST"
        parsed_links = json.loads(args.links_json)
        if not isinstance(parsed_links, list):
            raise ValueError("--links-json must be a JSON array")
        body = {"links": parsed_links}
    elif args.action == "inventory":
        method = "POST"
        body = {"collectionIDs": args.collection_ids}

    request = urllib.request.Request(
        f"{args.server_url.rstrip('/')}/pdf2zh-bridge/{endpoint}",
        data=json.dumps(body, separators=(",", ":")).encode("utf-8") if body else None,
        headers={
            "X-PDF2zh-Bridge-Token": token,
            "Zotero-Allowed-Request": "true",
            "User-Agent": "Codex-PDF2zh-Bridge/0.3",
            **({"Content-Type": "application/json; charset=utf-8"} if body else {}),
        },
        method=method,
    )
    with urllib.request.urlopen(request, timeout=args.timeout_seconds) as response:
        return json.load(response)


def positive(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def add_archive_metadata(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--template-item-id", type=positive)
    parser.add_argument("--item-type", default="conferencePaper")
    parser.add_argument("--title")
    parser.add_argument("--shortTitle", dest="shortTitle")
    parser.add_argument("--date")
    parser.add_argument("--DOI")
    parser.add_argument("--proceedingsTitle")
    parser.add_argument("--url")
    parser.add_argument("--pages")
    parser.add_argument("--language")
    parser.add_argument("--abstractNote")
    parser.add_argument("--creators-json")


def parse_args() -> argparse.Namespace:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--server-url", default="http://127.0.0.1:23119")
    common.add_argument("--token-path", type=Path, default=default_token_path())
    common.add_argument("--timeout-seconds", type=positive, default=120)
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="action", required=True)
    subparsers.add_parser("health", parents=[common])

    inventory = subparsers.add_parser("inventory", parents=[common])
    inventory.add_argument("--collection-id", dest="collection_ids", action="append",
                           required=True, type=positive)

    prepare = subparsers.add_parser("prepare", parents=[common])
    prepare.add_argument("--source-path", required=True, type=Path)
    prepare.add_argument("--target-collection-id", required=True, type=positive)
    prepare.add_argument("--short-title", required=True)

    archive = subparsers.add_parser("archive", parents=[common])
    archive.add_argument("--source-attachment-id", required=True, type=positive)
    archive.add_argument("--target-collection-id", required=True, type=positive)
    archive.add_argument("--translated-path", required=True, type=Path)
    archive.add_argument("--short-title", required=True)
    archive.add_argument("--service", default="siliconflowfree")
    add_archive_metadata(archive)

    github = subparsers.add_parser("github", parents=[common])
    github.add_argument("--links-json", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    token = read_token(args.token_path)
    response = request_bridge(args, token)
    print(json.dumps(response, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.HTTPError as error:
        detail = error.read(8192).decode("utf-8", errors="replace")
        try:
            payload = json.loads(detail)
            message = json.dumps(payload, ensure_ascii=False)
        except json.JSONDecodeError:
            message = f"HTTP {error.code}"
        print(f"ERROR: {message}", file=sys.stderr)
        raise SystemExit(1)
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
