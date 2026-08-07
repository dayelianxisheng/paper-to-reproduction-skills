#!/usr/bin/env python3
"""Create only the linked VLN-paper workspace directories."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


CANONICAL_SLUG = "dayelianxisheng/VLN-paper"


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def normalize_remote(remote: str) -> str:
    value = remote.strip().removesuffix(".git")
    if value.startswith("git@github.com:"):
        return value.removeprefix("git@github.com:")
    if value.startswith("https://github.com/"):
        return value.removeprefix("https://github.com/")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create notes/ without seeding user-facing content."
    )
    parser.add_argument("--repo", required=True, type=Path, help="VLN-paper repository root")
    parser.add_argument(
        "--allow-remote-mismatch",
        action="store_true",
        help="Initialize a test or fork whose origin does not match the canonical repository.",
    )
    args = parser.parse_args()

    repo = args.repo.expanduser().resolve()
    try:
        root = Path(run_git(repo, "rev-parse", "--show-toplevel")).resolve()
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        parser.error(f"not a Git repository: {repo} ({exc})")

    if root != repo:
        parser.error(f"--repo must be the repository root: expected {root}, got {repo}")

    try:
        remote = run_git(repo, "remote", "get-url", "origin")
    except subprocess.CalledProcessError:
        remote = ""
    slug = normalize_remote(remote)
    if slug != CANONICAL_SLUG and not args.allow_remote_mismatch:
        parser.error(
            f"origin mismatch: expected {CANONICAL_SLUG}, got {remote or '<missing>'}"
        )

    created: list[Path] = []
    for directory in (repo / "notes",):
        if not directory.exists():
            directory.mkdir(parents=True)
            created.append(directory)

    if created:
        print("Created:")
        for path in created:
            print(f"- {path.relative_to(repo)}/")
    else:
        print("Workspace directories already exist; no files changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
