#!/usr/bin/env python3
"""Discover, validate, cache, and read local paths for this skill."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import tempfile
from typing import Iterable


DIRECTORY_KEYS = {
    "pdf2zh_server_directory",
    "pdf2zh_source_directory",
    "pdf2zh_translated_directory",
    "zotero_data_directory",
}
FILE_KEYS = {
    "zotero_bridge_token_path",
    "uv_executable",
    "conda_executable",
    "python_executable",
    "terminal_executable",
    "powershell_executable",
    "wslpath_executable",
    "zotero_executable",
}
PATH_KEYS = DIRECTORY_KEYS | FILE_KEYS
ENV_PATHS = {
    "pdf2zh_server_directory": "PDF2ZH_SERVER_DIRECTORY",
    "pdf2zh_source_directory": "PDF2ZH_SOURCE_DIRECTORY",
    "pdf2zh_translated_directory": "PDF2ZH_TRANSLATED_DIRECTORY",
    "zotero_data_directory": "ZOTERO_DATA_DIRECTORY",
    "zotero_bridge_token_path": "PDF2ZH_BRIDGE_TOKEN_PATH",
}
TOOL_NAMES = {
    "uv_executable": ("uv",),
    "conda_executable": ("conda",),
    "python_executable": ("python3", "python", "py"),
    "terminal_executable": ("gnome-terminal", "xterm", "konsole", "xfce4-terminal"),
    "powershell_executable": ("powershell.exe", "powershell", "pwsh"),
    "wslpath_executable": ("wslpath",),
    "zotero_executable": ("zotero", "zotero.exe"),
}
PRUNED_DIRECTORIES = {
    ".cache",
    ".git",
    ".hg",
    ".npm",
    ".svn",
    "__pycache__",
    "node_modules",
    "site-packages",
    "storage",
    "translated",
    "zotero-pdf2zh-next-venv",
    "zotero-pdf2zh-venv",
}


def platform_name() -> str:
    if os.name == "nt":
        return "windows"
    release = platform.release().lower()
    if "microsoft" in release or "wsl" in release:
        return "wsl"
    if sys.platform.startswith("linux"):
        return "linux"
    return sys.platform


def default_config_path() -> Path:
    configured = os.environ.get("PDF2ZH_SKILL_CONFIG")
    if configured:
        return Path(configured).expanduser().resolve()
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        base_path = Path(base).expanduser() if base else Path.home()
    else:
        base = os.environ.get("XDG_CONFIG_HOME")
        base_path = Path(base).expanduser() if base else Path.home() / ".config"
    return (base_path / "translate-research-papers" / "local-paths.yaml").resolve()


def parse_scalar(value: str) -> object:
    value = value.strip()
    if not value:
        return ""
    if value in {"null", "~"}:
        return None
    if value in {"true", "false"}:
        return value == "true"
    if value.startswith(('"', "'")):
        return json.loads(value) if value.startswith('"') else value[1:-1]
    try:
        return int(value)
    except ValueError:
        return value


def load_config(path: Path | None = None) -> dict[str, object]:
    config_path = (path or default_config_path()).expanduser().resolve()
    if not config_path.is_file():
        return {}
    values: dict[str, object] = {}
    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        if key.replace("_", "").isalnum():
            values[key] = parse_scalar(raw_value)
    return values


def path_is_valid(key: str, value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    path = Path(value).expanduser()
    if key == "pdf2zh_server_directory":
        return path.is_dir() and (path / "server.py").is_file() and (
            path / "requirements.txt"
        ).is_file()
    if key in DIRECTORY_KEYS:
        return path.is_dir()
    if key in FILE_KEYS:
        return path.is_file()
    return False


def normalized_existing_path(key: str, value: str | Path) -> str | None:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    absolute = Path(os.path.abspath(path))
    if not path_is_valid(key, str(absolute)):
        return None
    return str(absolute)


def unique_existing_directories(values: Iterable[str | Path | None]) -> list[Path]:
    result: list[Path] = []
    seen: set[str] = set()
    for value in values:
        if not value:
            continue
        try:
            path = Path(value).expanduser().resolve(strict=True)
        except (FileNotFoundError, OSError):
            continue
        if path.is_file():
            path = path.parent
        marker = os.path.normcase(str(path))
        if path.is_dir() and marker not in seen:
            seen.add(marker)
            result.append(path)
    return result


def default_search_roots(extra: Iterable[Path], source: Path | None) -> list[Path]:
    environment_roots = [
        os.environ.get(name)
        for name in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "XDG_DATA_HOME")
    ]
    values: list[str | Path | None] = [*extra]
    if source:
        values.extend([source, source.parent])
    values.extend([Path.cwd(), *environment_roots, Path.home()])
    return unique_existing_directories(values)


def discover_by_signature(
    roots: Iterable[Path], max_depth: int
) -> tuple[Path | None, Path | None, Path | None]:
    server = None
    zotero_data = None
    token = None
    for root in roots:
        for current_text, directories, files in os.walk(root):
            current = Path(current_text)
            try:
                depth = len(current.relative_to(root).parts)
            except ValueError:
                continue
            directories[:] = [
                name
                for name in directories
                if name not in PRUNED_DIRECTORIES
                and (not name.startswith(".") or name == ".zotero")
            ]
            if depth >= max_depth:
                directories.clear()
            names = set(files)
            if server is None and {"server.py", "requirements.txt"} <= names:
                server = current.resolve()
            if zotero_data is None and "zotero.sqlite" in names:
                zotero_data = current.resolve()
            if token is None and "pdf2zh-bridge.token" in names:
                token = (current / "pdf2zh-bridge.token").resolve()
            if server and zotero_data and token:
                return server, zotero_data, token
    return server, zotero_data, token


def first_executable(names: Iterable[str]) -> str | None:
    for name in names:
        found = shutil.which(name)
        if found:
            resolved = normalized_existing_path("python_executable", found)
            if resolved:
                return resolved
    return None


def write_config(path: Path, values: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered_keys = ["version", "platform", "updated_at", *sorted(PATH_KEYS)]
    lines = ["# Generated by translate-research-papers; do not commit this file."]
    for key in ordered_keys:
        if key not in values:
            continue
        value = values[key]
        if isinstance(value, str):
            rendered = json.dumps(value, ensure_ascii=False)
        else:
            rendered = json.dumps(value)
        lines.append(f"{key}: {rendered}")
    content = "\n".join(lines) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def refresh_config(
    config_path: Path | None = None,
    *,
    source: Path | None = None,
    overrides: dict[str, Path | None] | None = None,
    search_roots: Iterable[Path] = (),
    max_depth: int = 7,
) -> tuple[Path, dict[str, object], list[str]]:
    path = (config_path or default_config_path()).expanduser().resolve()
    existing = load_config(path)
    values: dict[str, object] = {
        "version": 1,
        "platform": platform_name(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    for key in PATH_KEYS:
        if path_is_valid(key, existing.get(key)):
            normalized = normalized_existing_path(key, str(existing[key]))
            if normalized:
                values[key] = normalized

    supplied = dict(overrides or {})
    if source:
        supplied["pdf2zh_source_directory"] = source.resolve().parent
    for key, environment_name in ENV_PATHS.items():
        if key not in supplied and os.environ.get(environment_name):
            supplied[key] = Path(os.environ[environment_name])
    for key, candidate in supplied.items():
        if candidate is None:
            continue
        normalized = normalized_existing_path(key, candidate)
        if not normalized:
            raise FileNotFoundError(f"{key} does not exist or has the wrong type: {candidate}")
        values[key] = normalized

    for key, names in TOOL_NAMES.items():
        found = first_executable(names)
        if found:
            values[key] = found
        elif key in values and not path_is_valid(key, values[key]):
            values.pop(key, None)

    missing_discoverable = any(
        key not in values
        for key in (
            "pdf2zh_server_directory",
            "zotero_data_directory",
            "zotero_bridge_token_path",
        )
    )
    if missing_discoverable:
        roots = default_search_roots(search_roots, source)
        server, zotero_data, token = discover_by_signature(roots, max_depth)
        if server and "pdf2zh_server_directory" not in values:
            values["pdf2zh_server_directory"] = str(server)
        if zotero_data and "zotero_data_directory" not in values:
            values["zotero_data_directory"] = str(zotero_data)
        if token and "zotero_bridge_token_path" not in values:
            values["zotero_bridge_token_path"] = str(token)

    server_value = values.get("pdf2zh_server_directory")
    if server_value and "pdf2zh_translated_directory" not in values:
        translated = Path(str(server_value)) / "translated"
        normalized = normalized_existing_path("pdf2zh_translated_directory", translated)
        if normalized:
            values["pdf2zh_translated_directory"] = normalized

    zotero_value = values.get("zotero_data_directory")
    if zotero_value and "zotero_bridge_token_path" not in values:
        candidate = Path(str(zotero_value)) / "pdf2zh-bridge.token"
        normalized = normalized_existing_path("zotero_bridge_token_path", candidate)
        if normalized:
            values["zotero_bridge_token_path"] = normalized

    missing = sorted(key for key in DIRECTORY_KEYS | {"zotero_bridge_token_path"} if key not in values)
    write_config(path, values)
    return path, values, missing


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="action", required=True)

    refresh = subparsers.add_parser("refresh")
    refresh.add_argument("--config", type=Path)
    refresh.add_argument("--source", type=Path)
    refresh.add_argument("--server-directory", type=Path)
    refresh.add_argument("--source-directory", type=Path)
    refresh.add_argument("--translated-directory", type=Path)
    refresh.add_argument("--zotero-data-directory", type=Path)
    refresh.add_argument("--token-path", type=Path)
    refresh.add_argument("--search-root", action="append", default=[], type=Path)
    refresh.add_argument("--max-depth", type=int, default=7)

    get = subparsers.add_parser("get")
    get.add_argument("key", choices=sorted(PATH_KEYS))
    get.add_argument("--config", type=Path)

    show = subparsers.add_parser("show")
    show.add_argument("--config", type=Path)
    path = subparsers.add_parser("path")
    path.add_argument("--config", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = (args.config or default_config_path()).expanduser().resolve()
    if args.action == "refresh":
        if args.max_depth < 1:
            raise ValueError("--max-depth must be positive")
        source = args.source.expanduser().resolve(strict=True) if args.source else None
        if source and not source.is_file():
            raise ValueError(f"--source must be a file: {source}")
        overrides = {
            "pdf2zh_server_directory": args.server_directory,
            "pdf2zh_source_directory": args.source_directory,
            "pdf2zh_translated_directory": args.translated_directory,
            "zotero_data_directory": args.zotero_data_directory,
            "zotero_bridge_token_path": args.token_path,
        }
        path, values, missing = refresh_config(
            config_path,
            source=source,
            overrides=overrides,
            search_roots=args.search_root,
            max_depth=args.max_depth,
        )
        print(
            json.dumps(
                {
                    "status": "ok",
                    "config": str(path),
                    "savedKeys": sorted(key for key in values if key in PATH_KEYS),
                    "missingKeys": missing,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    values = load_config(config_path)
    if args.action == "path":
        print(config_path)
        return 0
    if args.action == "show":
        if not config_path.is_file():
            raise FileNotFoundError(f"local config does not exist: {config_path}")
        print(config_path.read_text(encoding="utf-8"), end="")
        return 0

    value = values.get(args.key)
    if not path_is_valid(args.key, value):
        raise FileNotFoundError(
            f"{args.key} is missing or stale; run local_config.py refresh"
        )
    normalized = normalized_existing_path(args.key, str(value))
    if not normalized:
        raise FileNotFoundError(
            f"{args.key} is missing or stale; run local_config.py refresh"
        )
    print(normalized)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
