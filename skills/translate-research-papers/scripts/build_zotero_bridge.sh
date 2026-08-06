#!/usr/bin/env bash
set -euo pipefail

script_directory=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source_directory=${1:-"$script_directory/zotero-bridge"}
output_path=${2:-"$script_directory/pdf2zh-bridge@codex.local.xpi"}

python3 - "$source_directory" "$output_path" <<'PY'
import json
import os
from pathlib import Path
import sys
import tempfile
import zipfile

source = Path(sys.argv[1]).expanduser().resolve()
output = Path(sys.argv[2]).expanduser().resolve()
required = (source / "manifest.json", source / "bootstrap.js")
if not all(path.is_file() for path in required):
    raise SystemExit(f"Bridge source is incomplete: {source}")

manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
version = manifest.get("version")
bootstrap = (source / "bootstrap.js").read_text(encoding="utf-8")
if f'version: "{version}"' not in bootstrap:
    raise SystemExit("manifest.json and bootstrap.js versions do not match")

output.parent.mkdir(parents=True, exist_ok=True)
descriptor, temporary_name = tempfile.mkstemp(
    prefix=output.name + ".", suffix=".tmp", dir=output.parent
)
os.close(descriptor)
temporary = Path(temporary_name)
try:
    with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source).as_posix())
    with zipfile.ZipFile(temporary) as archive:
        names = archive.namelist()
        if "manifest.json" not in names or "bootstrap.js" not in names:
            raise SystemExit("Built XPI is missing a root manifest or bootstrap script")
        json.loads(archive.read("manifest.json"))
    temporary.replace(output)
finally:
    if temporary.exists():
        temporary.unlink()

print(json.dumps({
    "status": "built",
    "version": version,
    "xpi": str(output),
    "bytes": output.stat().st_size,
    "entries": names,
}, indent=2))
PY
