#!/usr/bin/env python3
"""Collect non-destructive repository and host evidence for a readiness audit."""

from __future__ import annotations

import argparse
import ast
import ctypes
import ctypes.util
import datetime as dt
import importlib.metadata
import json
import locale
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterable


SCRIPT_VERSION = "0.1.0"
SCHEMA_VERSION = 1
MAX_COMMAND_OUTPUT = 12_000
DEFAULT_MAX_FILES = 20_000
DEFAULT_MAX_FILE_BYTES = 2 * 1024 * 1024
DEFAULT_COMMAND_TIMEOUT = 10.0

EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "build",
    "dist",
    "artifacts",
    "outputs",
    "output",
    "logs",
    "wandb",
    "data",
    "datasets",
    "checkpoints",
    "weights",
}

DEPENDENCY_BASENAMES = {
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "poetry.lock",
    "uv.lock",
    "pdm.lock",
    "pipfile",
    "pipfile.lock",
    "environment.yml",
    "environment.yaml",
    "package.xml",
    "cmakelists.txt",
    "colcon.meta",
    "colcon.defaults",
    "devcontainer.json",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
}

KNOWN_COMPONENTS = {
    "python": re.compile(r"\bpython(?:3)?\b", re.I),
    "torch": re.compile(r"\b(?:pytorch|torch)\b", re.I),
    "torchvision": re.compile(r"\btorchvision\b", re.I),
    "cuda": re.compile(r"\bcuda\b", re.I),
    "cudnn": re.compile(r"\bcudnn\b", re.I),
    "nccl": re.compile(r"\bnccl\b", re.I),
    "habitat-sim": re.compile(r"\bhabitat[-_ ]sim\b", re.I),
    "habitat-lab": re.compile(r"\bhabitat[-_ ]lab\b", re.I),
    "mattersim": re.compile(r"\bmatter(?:port)?sim\b", re.I),
    "gazebo": re.compile(r"\bgazebo\b", re.I),
    "ros-gz": re.compile(r"\bros[_-]gz\b", re.I),
    "isaac-sim": re.compile(r"\bisaac[-_ ]sim\b", re.I),
    "isaac-lab": re.compile(r"\bisaac[-_ ]lab\b", re.I),
    "airsim": re.compile(r"\bairsim\b", re.I),
    "unreal-engine": re.compile(r"\bunreal(?: engine)?\b", re.I),
    "mujoco": re.compile(r"\bmujoco\b", re.I),
    "detectron2": re.compile(r"\bdetectron2\b", re.I),
    "mmcv": re.compile(r"\bmmcv(?:-full)?\b", re.I),
    "xformers": re.compile(r"\bxformers\b", re.I),
    "flash-attn": re.compile(r"\bflash[-_ ]attn\b", re.I),
    "minkowski-engine": re.compile(r"\bminkowski(?:engine)?\b", re.I),
    "open3d": re.compile(r"\bopen3d\b", re.I),
}

PACKAGE_PROBES = [
    "torch",
    "torchvision",
    "torchaudio",
    "habitat-sim",
    "habitat-lab",
    "mujoco",
    "airsim",
    "isaacsim",
    "isaaclab",
    "detectron2",
    "mmcv",
    "mmcv-full",
    "xformers",
    "flash-attn",
    "MinkowskiEngine",
    "open3d",
    "matterport3d-simulator",
]

SAFE_ENV_KEYS = [
    "CONDA_DEFAULT_ENV",
    "CONDA_PREFIX",
    "VIRTUAL_ENV",
    "PYENV_VERSION",
    "CUDA_HOME",
    "CUDA_PATH",
    "CUDA_VISIBLE_DEVICES",
    "ROS_DISTRO",
    "ROS_VERSION",
    "RMW_IMPLEMENTATION",
    "WSL_DISTRO_NAME",
]

ENTRY_PREFIXES = (
    "python ",
    "python3 ",
    "torchrun ",
    "accelerate ",
    "deepspeed ",
    "bash ",
    "sh ",
    "roslaunch ",
    "ros2 launch ",
    "docker run ",
    "docker compose ",
    "podman run ",
)

ASSET_KEYWORDS = re.compile(
    r"\b(dataset|datasets|checkpoint|checkpoints|pretrained|pre-trained|"
    r"weights|model zoo|license|credential|token|api key|matterport|hm3d|"
    r"gibson|r2r|rxr|vln-ce)\b",
    re.I,
)

SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(token|password|passwd|secret|api[_-]?key|access[_-]?key)"
    r"\s*[:=]\s*([^\s,;]+)"
)
JSON_SECRET_ASSIGNMENT = re.compile(
    r'(?i)("?(?:token|password|passwd|secret|api[_-]?key|access[_-]?key)"?'
    r'\s*:\s*)("[^"]*"|[^,\s}\]]+)'
)
AUTHORIZATION_VALUE = re.compile(
    r"(?i)(authorization\s*[:=]\s*(?:bearer|basic)?\s*)[^\s,;]+"
)
URL_CREDENTIALS = re.compile(r"(https?://)([^/@\s]+)@")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Collect read-only host facts and repository dependency evidence. "
            "The output requires human/agent interpretation."
        )
    )
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    parser.add_argument(
        "--max-file-bytes", type=int, default=DEFAULT_MAX_FILE_BYTES
    )
    parser.add_argument(
        "--command-timeout", type=float, default=DEFAULT_COMMAND_TIMEOUT
    )
    parser.add_argument(
        "--no-command-probes",
        action="store_true",
        help="Scan files and Python metadata without launching version commands.",
    )
    return parser.parse_args()


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def decode_output(data: bytes | None) -> str:
    if not data:
        return ""
    encodings = ["utf-8", locale.getpreferredencoding(False)]
    if os.name == "nt":
        encodings.append("mbcs")
    for encoding in encodings:
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


def redact_text(value: str) -> str:
    text = str(value)
    home = str(Path.home())
    variants = {home, home.replace("\\", "/")}
    for variant in sorted(variants, key=len, reverse=True):
        if variant:
            text = re.sub(re.escape(variant), "<HOME>", text, flags=re.I)
    text = URL_CREDENTIALS.sub(r"\1<redacted>@", text)
    text = JSON_SECRET_ASSIGNMENT.sub(
        lambda match: f'{match.group(1)}"<redacted>"', text
    )
    text = SECRET_ASSIGNMENT.sub(
        lambda match: f"{match.group(1)}=<redacted>", text
    )
    text = AUTHORIZATION_VALUE.sub(
        lambda match: f"{match.group(1)}<redacted>", text
    )
    return text


def safe_path(path: str | Path) -> str:
    return redact_text(str(path))


def truncate(value: str, limit: int = MAX_COMMAND_OUTPUT) -> tuple[str, bool]:
    value = redact_text(value)
    if len(value) <= limit:
        return value, False
    return value[:limit] + "\n<output truncated>", True


def run_command(
    argv: list[str],
    *,
    cwd: Path | None = None,
    timeout: float = DEFAULT_COMMAND_TIMEOUT,
) -> dict[str, Any]:
    started = time.monotonic()
    executable = shutil.which(argv[0]) if not Path(argv[0]).exists() else argv[0]
    if not executable:
        return {
            "command": [safe_path(part) for part in argv],
            "available": False,
            "return_code": None,
            "timed_out": False,
            "duration_seconds": 0.0,
            "stdout": "",
            "stderr": "",
            "output_truncated": False,
        }

    command = [str(executable), *[str(part) for part in argv[1:]]]
    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
            shell=False,
            creationflags=creationflags,
        )
        stdout, stdout_truncated = truncate(decode_output(completed.stdout))
        stderr, stderr_truncated = truncate(decode_output(completed.stderr))
        return {
            "command": [safe_path(part) for part in command],
            "available": True,
            "return_code": completed.returncode,
            "timed_out": False,
            "duration_seconds": round(time.monotonic() - started, 3),
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
            "output_truncated": stdout_truncated or stderr_truncated,
        }
    except subprocess.TimeoutExpired as exc:
        stdout, stdout_truncated = truncate(decode_output(exc.stdout))
        stderr, stderr_truncated = truncate(decode_output(exc.stderr))
        return {
            "command": [safe_path(part) for part in command],
            "available": True,
            "return_code": None,
            "timed_out": True,
            "duration_seconds": round(time.monotonic() - started, 3),
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
            "output_truncated": stdout_truncated or stderr_truncated,
        }
    except OSError as exc:
        return {
            "command": [safe_path(part) for part in command],
            "available": True,
            "return_code": None,
            "timed_out": False,
            "duration_seconds": round(time.monotonic() - started, 3),
            "stdout": "",
            "stderr": redact_text(f"{type(exc).__name__}: {exc}"),
            "output_truncated": False,
        }


def tool_presence(name: str) -> dict[str, Any]:
    path = shutil.which(name)
    return {"available": bool(path), "path": safe_path(path) if path else None}


def windows_memory() -> dict[str, int | None]:
    class MemoryStatusEx(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = MemoryStatusEx()
    status.dwLength = ctypes.sizeof(MemoryStatusEx)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return {}
    return {
        "ram_total_bytes": int(status.ullTotalPhys),
        "ram_available_bytes": int(status.ullAvailPhys),
        "swap_total_bytes": max(
            0, int(status.ullTotalPageFile - status.ullTotalPhys)
        ),
        "swap_available_bytes": max(
            0, int(status.ullAvailPageFile - status.ullAvailPhys)
        ),
    }


def proc_memory() -> dict[str, int | None]:
    path = Path("/proc/meminfo")
    if not path.exists():
        return {}
    values: dict[str, int] = {}
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            name, raw = line.split(":", 1)
            match = re.search(r"(\d+)", raw)
            if match:
                values[name] = int(match.group(1)) * 1024
    except (OSError, ValueError):
        return {}
    return {
        "ram_total_bytes": values.get("MemTotal"),
        "ram_available_bytes": values.get("MemAvailable"),
        "swap_total_bytes": values.get("SwapTotal"),
        "swap_available_bytes": values.get("SwapFree"),
    }


def collect_host(repo_root: Path) -> dict[str, Any]:
    memory: dict[str, Any] = {}
    if os.name == "nt":
        try:
            memory = windows_memory()
        except (AttributeError, OSError):
            memory = {}
    elif sys.platform.startswith("linux"):
        memory = proc_memory()

    disk = shutil.disk_usage(repo_root)
    release = platform.release()
    is_wsl = bool(
        re.search(r"microsoft|wsl", release, re.I)
        or os.environ.get("WSL_DISTRO_NAME")
    )
    container_markers = [
        path
        for path in (Path("/.dockerenv"), Path("/run/.containerenv"))
        if path.exists()
    ]
    safe_env: dict[str, str] = {}
    for key in SAFE_ENV_KEYS:
        value = os.environ.get(key)
        if value:
            safe_env[key] = redact_text(value)
    safe_env.update(
        {
            "DISPLAY_SET": str(bool(os.environ.get("DISPLAY"))),
            "WAYLAND_DISPLAY_SET": str(bool(os.environ.get("WAYLAND_DISPLAY"))),
            "XDG_SESSION_TYPE": os.environ.get("XDG_SESSION_TYPE", ""),
        }
    )

    return {
        "os": platform.system(),
        "os_release": platform.release(),
        "os_version": platform.version(),
        "kernel": platform.platform(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "logical_cpu_count": os.cpu_count(),
        **memory,
        "disk": {
            "path": safe_path(repo_root.anchor or repo_root),
            "total_bytes": disk.total,
            "used_bytes": disk.used,
            "free_bytes": disk.free,
        },
        "wsl": is_wsl,
        "container": {
            "detected": bool(container_markers or os.environ.get("container")),
            "markers": [safe_path(path) for path in container_markers],
            "environment_hint": os.environ.get("container"),
        },
        "current_python": {
            "executable": safe_path(sys.executable),
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "prefix": safe_path(sys.prefix),
            "base_prefix": safe_path(sys.base_prefix),
        },
        "safe_environment": safe_env,
    }


def unique_existing_paths(values: Iterable[str | Path | None]) -> list[Path]:
    result: list[Path] = []
    seen: set[str] = set()
    for value in values:
        if not value:
            continue
        path = Path(str(value)).expanduser()
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path.absolute()
        key = os.path.normcase(str(resolved))
        if key not in seen and resolved.exists():
            seen.add(key)
            result.append(resolved)
    return result


def collect_python_interpreters(
    command_timeout: float, no_commands: bool
) -> dict[str, Any]:
    candidates: list[str | Path | None] = [
        sys.executable,
        shutil.which("python"),
        shutil.which("python3"),
    ]
    discovery: dict[str, Any] = {}
    if not no_commands and os.name == "nt":
        where_result = run_command(
            ["where.exe", "python"], timeout=command_timeout
        )
        discovery["where_python"] = where_result
        if where_result["return_code"] == 0:
            candidates.extend(where_result["stdout"].splitlines())
        launcher = run_command(["py", "-0p"], timeout=command_timeout)
        discovery["py_launcher"] = launcher
        if launcher["return_code"] == 0:
            for line in launcher["stdout"].splitlines():
                match = re.search(r"([A-Za-z]:[\\/].*?python(?:\.exe)?)\s*$", line)
                if match:
                    candidates.append(match.group(1))
    elif not no_commands:
        for command in ("python", "python3"):
            which_result = run_command(
                ["which", "-a", command], timeout=command_timeout
            )
            discovery[f"which_{command}"] = which_result
            if which_result["return_code"] == 0:
                candidates.extend(which_result["stdout"].splitlines())

    interpreters = []
    for path in unique_existing_paths(candidates):
        version = (
            run_command([str(path), "--version"], timeout=command_timeout)
            if not no_commands
            else None
        )
        interpreters.append({"path": safe_path(path), "version_probe": version})
    return {"interpreters": interpreters, "discovery": discovery}


def probe_tools(
    command_timeout: float, no_commands: bool
) -> dict[str, dict[str, Any]]:
    specs = {
        "pip": ["--version"],
        "conda": ["--version"],
        "mamba": ["--version"],
        "micromamba": ["--version"],
        "uv": ["--version"],
        "poetry": ["--version"],
        "pipenv": ["--version"],
        "git": ["--version"],
        "gcc": ["--version"],
        "g++": ["--version"],
        "clang": ["--version"],
        "clang++": ["--version"],
        "cmake": ["--version"],
        "ninja": ["--version"],
        "make": ["--version"],
        "msbuild": ["-version"],
        "cl": [],
        "docker": ["--version"],
        "podman": ["--version"],
        "apptainer": ["--version"],
        "singularity": ["--version"],
        "nvidia-container-cli": ["--version"],
        "rosversion": ["-d"],
        "ros2": ["--help"],
        "colcon": ["--help"],
        "rosdep": ["--version"],
        "gazebo": ["--version"],
        "gz": ["--version"],
    }
    presence_only = [
        "Xvfb",
        "vulkaninfo",
        "glxinfo",
        "UnrealEditor",
        "UnrealEditor-Cmd",
        "isaac-sim.sh",
        "isaac-sim.bat",
    ]
    result: dict[str, dict[str, Any]] = {}
    for name, args in specs.items():
        if no_commands:
            result[name] = tool_presence(name)
        else:
            result[name] = run_command(
                [name, *args], timeout=command_timeout
            )
    for name in presence_only:
        result[name] = tool_presence(name)
    return result


def collect_conda_environments(
    command_timeout: float, no_commands: bool
) -> dict[str, Any]:
    if no_commands or not shutil.which("conda"):
        return {"available": bool(shutil.which("conda")), "probe": None}
    return {
        "available": True,
        "probe": run_command(["conda", "--version"], timeout=command_timeout),
        "environment_listing": (
            "not_collected: Conda environment listings can expose user-specific "
            "paths or environment metadata"
        ),
    }


def collect_nvidia(
    command_timeout: float, no_commands: bool
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "driver_capability": None,
        "gpus": None,
        "toolkit_nvcc": None,
        "cudnn_indicators": [],
    }
    if no_commands:
        result["nvidia_smi"] = tool_presence("nvidia-smi")
        result["nvcc"] = tool_presence("nvcc")
    else:
        summary = run_command(["nvidia-smi"], timeout=command_timeout)
        result["nvidia_smi"] = summary
        match = re.search(
            r"CUDA(?:\s+UMD)?\s+Version:\s*([0-9.]+)",
            summary.get("stdout", ""),
        )
        if match:
            result["driver_capability"] = match.group(1)

        query = run_command(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,driver_version,compute_cap",
                "--format=csv,noheader,nounits",
            ],
            timeout=command_timeout,
        )
        if query["available"] and query["return_code"] != 0:
            query = run_command(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total,driver_version",
                    "--format=csv,noheader,nounits",
                ],
                timeout=command_timeout,
            )
        result["gpu_query"] = query
        if query["return_code"] == 0:
            result["gpus"] = []
            for line in query["stdout"].splitlines():
                if not line.strip():
                    continue
                parts = [part.strip() for part in line.split(",")]
                gpu = {
                    "name": parts[0] if len(parts) > 0 else None,
                    "memory_total_mib": parts[1] if len(parts) > 1 else None,
                    "driver_version": parts[2] if len(parts) > 2 else None,
                    "compute_capability": parts[3] if len(parts) > 3 else None,
                }
                result["gpus"].append(gpu)
        nvcc = run_command(["nvcc", "--version"], timeout=command_timeout)
        result["nvcc"] = nvcc
        if nvcc["return_code"] == 0:
            match = re.search(r"release\s+([0-9.]+)", nvcc["stdout"], re.I)
            if match:
                result["toolkit_nvcc"] = match.group(1)

    cuda_roots = unique_existing_paths(
        [os.environ.get("CUDA_PATH"), os.environ.get("CUDA_HOME")]
    )
    for root in cuda_roots:
        for relative in (
            "include/cudnn_version.h",
            "include/cudnn.h",
            "bin/cudnn64_9.dll",
            "bin/cudnn64_8.dll",
            "lib64/libcudnn.so",
        ):
            candidate = root / relative
            if candidate.exists():
                result["cudnn_indicators"].append(safe_path(candidate))
    return result


def collect_torch(command_timeout: float, no_commands: bool) -> dict[str, Any]:
    if no_commands:
        try:
            version = importlib.metadata.version("torch")
            return {"installed": True, "version": version, "runtime_probe": None}
        except importlib.metadata.PackageNotFoundError:
            return {"installed": False, "version": None, "runtime_probe": None}

    code = (
        "import json\n"
        "try:\n"
        " import torch\n"
        " devices=[]\n"
        " for i in range(torch.cuda.device_count()):\n"
        "  p=torch.cuda.get_device_properties(i)\n"
        "  devices.append({'index':i,'name':p.name,'total_memory':p.total_memory,"
        "'compute_capability':list(torch.cuda.get_device_capability(i))})\n"
        " print(json.dumps({'installed':True,'version':torch.__version__,"
        "'compiled_cuda':torch.version.cuda,'cuda_available':torch.cuda.is_available(),"
        "'device_count':torch.cuda.device_count(),'devices':devices}))\n"
        "except Exception as e:\n"
        " print(json.dumps({'installed':False,'error':type(e).__name__+': '+str(e)}))\n"
    )
    probe = run_command(
        [sys.executable, "-c", code],
        timeout=max(command_timeout, 20.0),
    )
    parsed = None
    if probe["return_code"] == 0 and probe["stdout"]:
        try:
            parsed = json.loads(probe["stdout"].splitlines()[-1])
        except json.JSONDecodeError:
            parsed = None
    return {"probe": probe, "facts": parsed}


def collect_packages() -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for name in PACKAGE_PROBES:
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = None
        except Exception as exc:  # metadata providers can be broken
            result[name] = f"ERROR: {type(exc).__name__}"
    return result


def collect_rendering() -> dict[str, Any]:
    libraries = {}
    for name in ("EGL", "OSMesa", "GL", "OpenGL", "vulkan"):
        try:
            libraries[name] = ctypes.util.find_library(name)
        except (OSError, AttributeError):
            libraries[name] = None
    return {
        "display_set": bool(os.environ.get("DISPLAY")),
        "wayland_display_set": bool(os.environ.get("WAYLAND_DISPLAY")),
        "xdg_session_type": os.environ.get("XDG_SESSION_TYPE"),
        "libraries": libraries,
        "executables": {
            name: tool_presence(name)
            for name in ("Xvfb", "vulkaninfo", "glxinfo")
        },
    }


def collect_git(
    repo_root: Path, command_timeout: float, no_commands: bool
) -> dict[str, Any]:
    if no_commands or not shutil.which("git"):
        return {"available": bool(shutil.which("git")), "probes": {}}

    commands = {
        "root": ["git", "-C", str(repo_root), "rev-parse", "--show-toplevel"],
        "commit": ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        "branch": [
            "git",
            "-C",
            str(repo_root),
            "branch",
            "--show-current",
        ],
        "status": [
            "git",
            "-C",
            str(repo_root),
            "status",
            "--porcelain=v1",
        ],
        "remotes": ["git", "-C", str(repo_root), "remote", "-v"],
        "submodules": [
            "git",
            "-C",
            str(repo_root),
            "submodule",
            "status",
            "--recursive",
        ],
        "tags": [
            "git",
            "-C",
            str(repo_root),
            "tag",
            "--points-at",
            "HEAD",
        ],
        "lfs": ["git", "lfs", "version"],
    }
    probes = {
        name: run_command(argv, timeout=command_timeout)
        for name, argv in commands.items()
    }
    return {
        "available": True,
        "is_repository": probes["root"]["return_code"] == 0,
        "dirty_entry_count": len(
            [
                line
                for line in probes["status"].get("stdout", "").splitlines()
                if line.strip()
            ]
        ),
        "probes": probes,
    }


def is_dependency_file(relative: Path) -> bool:
    name = relative.name.lower()
    rel = relative.as_posix().lower()
    if name in DEPENDENCY_BASENAMES:
        return True
    if name.startswith(("requirements", "constraints")) and name.endswith(".txt"):
        return True
    if name.startswith(("environment", "conda")) and name.endswith(
        (".yml", ".yaml")
    ):
        return True
    if name.startswith("dockerfile"):
        return True
    if name.endswith(".repos"):
        return True
    if name.startswith(("install", "build")) and name.endswith(
        (".sh", ".ps1", ".bat", ".cmd")
    ):
        return True
    if rel.startswith(".github/workflows/") and name.endswith((".yml", ".yaml")):
        return True
    if ".devcontainer/" in f"/{rel}" and name.endswith((".json", ".yml", ".yaml")):
        return True
    return False


def is_documentation_file(relative: Path) -> bool:
    name = relative.name.lower()
    rel = relative.as_posix().lower()
    if name.startswith("readme"):
        return True
    if rel.startswith(("docs/", "doc/")) and name.endswith(
        (".md", ".rst", ".txt")
    ):
        return True
    if any(
        word in name
        for word in (
            "install",
            "dataset",
            "checkpoint",
            "pretrain",
            "simulator",
            "benchmark",
            "license",
        )
    ) and name.endswith((".md", ".rst", ".txt")):
        return True
    return False


def read_text(path: Path, max_file_bytes: int) -> str | None:
    try:
        if path.stat().st_size > max_file_bytes:
            return None
        if path.name.lower() == ".env":
            return None
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return None


def provisional_classification(
    evidence_type: str, source_name: str, raw: str
) -> tuple[str, str, str]:
    lower = raw.lower()
    name = source_name.lower()
    if "optional" in lower or "extra" in lower:
        return "optional", "medium", "Source text marks this path as optional."
    if evidence_type in {"runtime_assertion", "python_requires"}:
        return "hard", "medium", "Runtime or package metadata constrains execution."
    if evidence_type == "ros_manifest":
        return "hard", "medium", "ROS manifest declares a package dependency."
    if evidence_type == "cmake_required":
        return "hard", "medium", "CMake marks the component REQUIRED."
    if "lock" in name or name.startswith("constraints"):
        return "hard", "medium", "Lock or constraints evidence is an exact environment candidate."
    if evidence_type in {"ci", "container", "environment"}:
        return "recommended", "medium", "Represents an authored or tested environment."
    if evidence_type in {"source_import", "documentation", "cmake"}:
        return "unknown", "low", "Heuristic evidence requires reconciliation."
    return "unknown", "medium", "Raw dependency evidence requires reconciliation."


def add_evidence(
    records: list[dict[str, Any]],
    seen: set[tuple[Any, ...]],
    *,
    component: str,
    constraint: str | None,
    source_path: str,
    line: int | None,
    section: str | None,
    evidence_type: str,
    raw: str,
) -> None:
    component = component.strip().lower().replace("_", "-")
    if not component:
        return
    raw_clean, _ = truncate(raw.strip(), 500)
    key = (component, constraint or "", source_path, line, evidence_type)
    if key in seen or len(records) >= 5_000:
        return
    seen.add(key)
    classification, confidence, reason = provisional_classification(
        evidence_type, Path(source_path).name, raw_clean
    )
    records.append(
        {
            "component": component,
            "constraint": constraint,
            "source_path": source_path,
            "line": line,
            "section": section,
            "evidence_type": evidence_type,
            "classification": classification,
            "confidence": confidence,
            "reason": reason,
            "raw": redact_text(raw_clean),
            "conflicts": [],
            "agent_reviewed": False,
        }
    )


def requirement_match(line: str) -> tuple[str, str | None] | None:
    value = line.strip()
    if (
        not value
        or value.startswith(("#", "-", "http://", "https://", "git+"))
        or "://" in value
    ):
        return None
    value = value.split(";", 1)[0].strip()
    match = re.match(
        r"^([A-Za-z0-9][A-Za-z0-9_.-]*)(?:\[[^\]]+\])?\s*"
        r"([!<>=~].+)?$",
        value,
    )
    if not match:
        return None
    return match.group(1), match.group(2).strip() if match.group(2) else None


def source_imports(
    text: str, source_path: str
) -> list[tuple[str, int | None, str]]:
    result: list[tuple[str, int | None, str]] = []
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return result
    seen: set[str] = set()
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name.split(".", 1)[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module.split(".", 1)[0]]
        for name in names:
            if name and name not in seen and not name.startswith("_"):
                seen.add(name)
                result.append((name, getattr(node, "lineno", None), source_path))
    return result


def scan_repository(
    repo_root: Path,
    output_dir: Path,
    max_files: int,
    max_file_bytes: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    evidence_seen: set[tuple[Any, ...]] = set()
    dependency_files: list[str] = []
    documentation_files: list[str] = []
    source_files_scanned = 0
    candidate_files_scanned = 0
    skipped_large: list[str] = []
    unreadable: list[str] = []
    entry_commands: list[dict[str, Any]] = []
    asset_hints: list[dict[str, Any]] = []
    license_files: list[str] = []
    credential_hints: list[str] = []
    visited_files = 0
    truncated_scan = False

    output_resolved = output_dir.resolve()
    for current, dirs, files in os.walk(repo_root):
        current_path = Path(current)
        dirs[:] = [
            name
            for name in dirs
            if name.lower() not in EXCLUDED_DIRS
            and not (current_path / name).is_symlink()
            and (current_path / name).resolve() != output_resolved
        ]
        for filename in files:
            visited_files += 1
            if visited_files > max_files:
                truncated_scan = True
                break
            path = current_path / filename
            if path.is_symlink():
                continue
            try:
                relative = path.relative_to(repo_root)
            except ValueError:
                continue
            rel_text = relative.as_posix()
            lower_name = filename.lower()
            if lower_name.startswith(".env") and lower_name not in {
                ".env.example",
                ".env.sample",
                ".env.template",
            }:
                credential_hints.append(rel_text)
                continue
            if lower_name.startswith(("license", "copying")):
                license_files.append(rel_text)

            dependency_file = is_dependency_file(relative)
            documentation_file = is_documentation_file(relative)
            source_file = lower_name.endswith(
                (".py", ".cmake", ".xml", ".launch", ".launch.py")
            ) or lower_name == "cmakelists.txt"
            if not (dependency_file or documentation_file or source_file):
                continue
            try:
                if path.stat().st_size > max_file_bytes:
                    skipped_large.append(rel_text)
                    continue
            except OSError:
                unreadable.append(rel_text)
                continue
            text = read_text(path, max_file_bytes)
            if text is None:
                unreadable.append(rel_text)
                continue

            candidate_files_scanned += 1
            if dependency_file:
                dependency_files.append(rel_text)
            if documentation_file:
                documentation_files.append(rel_text)
            if source_file:
                source_files_scanned += 1

            lines = text.splitlines()
            base = lower_name
            for line_number, line in enumerate(lines, start=1):
                stripped = line.strip().lstrip("$>").strip()
                if not stripped:
                    continue

                if base.startswith(("requirements", "constraints")) and base.endswith(
                    ".txt"
                ):
                    match = requirement_match(stripped)
                    if match:
                        add_evidence(
                            records,
                            evidence_seen,
                            component=match[0],
                            constraint=match[1],
                            source_path=rel_text,
                            line=line_number,
                            section=None,
                            evidence_type="requirements",
                            raw=line,
                        )

                if base in {"environment.yml", "environment.yaml"}:
                    match = re.match(
                        r"^\s*-\s*([A-Za-z0-9][A-Za-z0-9_.-]*)"
                        r"\s*([=<>!~].+)?$",
                        line,
                    )
                    if match:
                        add_evidence(
                            records,
                            evidence_seen,
                            component=match.group(1),
                            constraint=(
                                match.group(2).strip() if match.group(2) else None
                            ),
                            source_path=rel_text,
                            line=line_number,
                            section=None,
                            evidence_type="environment",
                            raw=line,
                        )

                if base in {"pyproject.toml", "setup.py", "setup.cfg"}:
                    python_match = re.search(
                        r"(?:requires-python|python_requires)\s*[:=]\s*[\"']([^\"']+)",
                        line,
                        re.I,
                    )
                    if python_match:
                        add_evidence(
                            records,
                            evidence_seen,
                            component="python",
                            constraint=python_match.group(1).strip(),
                            source_path=rel_text,
                            line=line_number,
                            section=None,
                            evidence_type="python_requires",
                            raw=line,
                        )
                    dep_match = re.search(
                        r"[\"']([A-Za-z0-9][A-Za-z0-9_.-]*)"
                        r"(?:\[[^\]]+\])?\s*([!<>=~][^\"']+)?[\"']",
                        line,
                    )
                    if dep_match and dep_match.group(1).lower() not in {
                        "name",
                        "version",
                        "description",
                    }:
                        add_evidence(
                            records,
                            evidence_seen,
                            component=dep_match.group(1),
                            constraint=(
                                dep_match.group(2).strip()
                                if dep_match.group(2)
                                else None
                            ),
                            source_path=rel_text,
                            line=line_number,
                            section=None,
                            evidence_type="package_metadata",
                            raw=line,
                        )

                if base.startswith("dockerfile"):
                    image = re.match(r"^\s*FROM\s+([^\s]+)", line, re.I)
                    if image:
                        add_evidence(
                            records,
                            evidence_seen,
                            component="container-base-image",
                            constraint=image.group(1),
                            source_path=rel_text,
                            line=line_number,
                            section=None,
                            evidence_type="container",
                            raw=line,
                        )

                if rel_text.lower().startswith(".github/workflows/"):
                    ci_match = re.search(
                        r"(?:python-version|cuda|runs-on|container)\s*:\s*"
                        r"[\"']?([^#\"']+)",
                        line,
                        re.I,
                    )
                    if ci_match:
                        component = (
                            "python"
                            if "python-version" in line.lower()
                            else "ci-environment"
                        )
                        add_evidence(
                            records,
                            evidence_seen,
                            component=component,
                            constraint=ci_match.group(1).strip(),
                            source_path=rel_text,
                            line=line_number,
                            section=None,
                            evidence_type="ci",
                            raw=line,
                        )

                ros_match = re.search(
                    r"<(depend|build_depend|exec_depend|buildtool_depend|test_depend)>"
                    r"\s*([^<\s]+)\s*</",
                    line,
                    re.I,
                )
                if ros_match:
                    evidence_type = (
                        "ros_manifest"
                        if ros_match.group(1).lower() != "test_depend"
                        else "optional"
                    )
                    add_evidence(
                        records,
                        evidence_seen,
                        component=ros_match.group(2),
                        constraint=None,
                        source_path=rel_text,
                        line=line_number,
                        section=ros_match.group(1),
                        evidence_type=evidence_type,
                        raw=line,
                    )

                cmake_match = re.search(
                    r"find_package\s*\(\s*([A-Za-z0-9_.+-]+)([^)]*)\)",
                    line,
                    re.I,
                )
                if cmake_match:
                    tail = cmake_match.group(2)
                    version = None
                    version_match = re.search(r"\b([0-9]+(?:\.[0-9]+)+)\b", tail)
                    if version_match:
                        version = version_match.group(1)
                    add_evidence(
                        records,
                        evidence_seen,
                        component=cmake_match.group(1),
                        constraint=version,
                        source_path=rel_text,
                        line=line_number,
                        section=None,
                        evidence_type=(
                            "cmake_required"
                            if re.search(r"\bREQUIRED\b", tail, re.I)
                            else "cmake"
                        ),
                        raw=line,
                    )

                if re.search(
                    r"\b(assert|raise|check).{0,80}\b(version|cuda|cudnn|python)",
                    line,
                    re.I,
                ):
                    add_evidence(
                        records,
                        evidence_seen,
                        component="runtime-version-check",
                        constraint=None,
                        source_path=rel_text,
                        line=line_number,
                        section=None,
                        evidence_type="runtime_assertion",
                        raw=line,
                    )

                for component, pattern in KNOWN_COMPONENTS.items():
                    if pattern.search(line):
                        version = None
                        version_match = re.search(
                            r"(?:==|>=|<=|~=|>|<|version[:= ]+|v)"
                            r"\s*([0-9]+(?:\.[0-9A-Za-z*+_-]+)+)",
                            line,
                            re.I,
                        )
                        if version_match:
                            version = version_match.group(1)
                        add_evidence(
                            records,
                            evidence_seen,
                            component=component,
                            constraint=version,
                            source_path=rel_text,
                            line=line_number,
                            section=None,
                            evidence_type=(
                                "documentation"
                                if documentation_file
                                else "source_reference"
                            ),
                            raw=line,
                        )

                if stripped.lower().startswith(ENTRY_PREFIXES):
                    if len(entry_commands) < 250:
                        entry_commands.append(
                            {
                                "source_path": rel_text,
                                "line": line_number,
                                "command": redact_text(stripped[:1_000]),
                            }
                        )
                if ASSET_KEYWORDS.search(line) and len(asset_hints) < 500:
                    asset_hints.append(
                        {
                            "source_path": rel_text,
                            "line": line_number,
                            "text": redact_text(stripped[:500]),
                        }
                    )

            if lower_name.endswith(".py") and source_files_scanned <= 2_000:
                for component, line_number, _ in source_imports(text, rel_text):
                    add_evidence(
                        records,
                        evidence_seen,
                        component=component,
                        constraint=None,
                        source_path=rel_text,
                        line=line_number,
                        section=None,
                        evidence_type="source_import",
                        raw=f"import {component}",
                    )
        if truncated_scan:
            break

    root_assets = []
    for path in repo_root.iterdir():
        if path.name.lower() in {
            "data",
            "dataset",
            "datasets",
            "checkpoint",
            "checkpoints",
            "weights",
            "models",
            "assets",
        }:
            root_assets.append(
                {
                    "path": path.name,
                    "exists": True,
                    "kind": "directory" if path.is_dir() else "file",
                }
            )

    scan = {
        "visited_files": visited_files,
        "candidate_files_scanned": candidate_files_scanned,
        "source_files_scanned": source_files_scanned,
        "max_files": max_files,
        "max_file_bytes": max_file_bytes,
        "truncated": truncated_scan,
        "dependency_files": sorted(set(dependency_files)),
        "documentation_files": sorted(set(documentation_files)),
        "skipped_large": sorted(set(skipped_large)),
        "unreadable": sorted(set(unreadable)),
        "license_files": sorted(set(license_files)),
        "credential_file_hints": sorted(set(credential_hints)),
        "root_asset_paths": root_assets,
        "entry_command_candidates": entry_commands,
        "asset_and_license_hints": asset_hints,
    }
    return scan, records


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_verification_commands(output_dir: Path) -> None:
    shell_text = """#!/usr/bin/env sh
set -eu
# Read-only commands. Run from the repository root and inspect every failure.
python3 --version
git --version
command -v uv >/dev/null 2>&1 && uv --version || true
command -v conda >/dev/null 2>&1 && conda --version || true
command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi || true
command -v nvcc >/dev/null 2>&1 && nvcc --version || true
command -v cmake >/dev/null 2>&1 && cmake --version || true
command -v docker >/dev/null 2>&1 && docker --version || true
command -v ros2 >/dev/null 2>&1 && ros2 --help >/dev/null || true
# Add repository-specific import/config/test commands only after review.
"""
    powershell_text = """$ErrorActionPreference = "Continue"
# Read-only commands. Run from the repository root and inspect every failure.
python --version
git --version
if (Get-Command uv -ErrorAction SilentlyContinue) { uv --version }
if (Get-Command conda -ErrorAction SilentlyContinue) { conda --version }
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) { nvidia-smi }
if (Get-Command nvcc -ErrorAction SilentlyContinue) { nvcc --version }
if (Get-Command cmake -ErrorAction SilentlyContinue) { cmake --version }
if (Get-Command docker -ErrorAction SilentlyContinue) { docker --version }
if (Get-Command ros2 -ErrorAction SilentlyContinue) { ros2 --help | Out-Null }
# Add repository-specific import/config/test commands only after review.
"""
    (output_dir / "commands_to_verify.sh").write_text(shell_text, encoding="utf-8")
    (output_dir / "commands_to_verify.ps1").write_text(
        powershell_text, encoding="utf-8"
    )


def main() -> int:
    args = parse_args()
    if (
        args.max_files < 1
        or args.max_file_bytes < 1
        or args.command_timeout <= 0
    ):
        raise ValueError("Scan limits and command timeout must be positive.")

    repo_root = args.repo_root.expanduser().resolve()
    if not repo_root.is_dir():
        raise ValueError(f"Repository root is not a directory: {repo_root}")
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    generated_at = now_utc()
    host = collect_host(repo_root)
    python_info = collect_python_interpreters(
        args.command_timeout, args.no_command_probes
    )
    tools = probe_tools(args.command_timeout, args.no_command_probes)
    conda = collect_conda_environments(
        args.command_timeout, args.no_command_probes
    )
    nvidia = collect_nvidia(args.command_timeout, args.no_command_probes)
    torch = collect_torch(args.command_timeout, args.no_command_probes)
    packages = collect_packages()
    rendering = collect_rendering()
    git = collect_git(
        repo_root, args.command_timeout, args.no_command_probes
    )
    scan, evidence = scan_repository(
        repo_root,
        output_dir,
        args.max_files,
        args.max_file_bytes,
    )

    environment_probe = {
        "schema_version": SCHEMA_VERSION,
        "script_version": SCRIPT_VERSION,
        "generated_at": generated_at,
        "repo_root": safe_path(repo_root),
        "output_dir": safe_path(output_dir),
        "non_destructive": True,
        "command_probes_enabled": not args.no_command_probes,
        "host": host,
        "python": python_info,
        "environment_managers": {"conda": conda},
        "tools": tools,
        "nvidia": nvidia,
        "pytorch": torch,
        "selected_python_packages": packages,
        "ros": {
            "environment": {
                key: os.environ.get(key)
                for key in ("ROS_DISTRO", "ROS_VERSION", "RMW_IMPLEMENTATION")
                if os.environ.get(key)
            },
            "tools": {
                key: tools.get(key)
                for key in ("rosversion", "ros2", "colcon", "rosdep")
            },
        },
        "containers": {
            key: tools.get(key)
            for key in (
                "docker",
                "podman",
                "apptainer",
                "singularity",
                "nvidia-container-cli",
            )
        },
        "simulators": {
            "packages": {
                key: packages.get(key)
                for key in (
                    "habitat-sim",
                    "habitat-lab",
                    "mujoco",
                    "airsim",
                    "isaacsim",
                    "isaaclab",
                )
            },
            "tools": {
                key: tools.get(key)
                for key in (
                    "gazebo",
                    "gz",
                    "UnrealEditor",
                    "UnrealEditor-Cmd",
                    "isaac-sim.sh",
                    "isaac-sim.bat",
                )
            },
        },
        "rendering": rendering,
        "git": git,
        "warnings": [
            "nvidia-smi CUDA Version is driver capability, not the installed toolkit.",
            "Absence from PATH is not proof that software is absent elsewhere.",
            "No credential values were collected.",
            "Probe output requires agent review before compatibility conclusions.",
        ],
    }
    dependency_evidence = {
        "schema_version": SCHEMA_VERSION,
        "script_version": SCRIPT_VERSION,
        "generated_at": generated_at,
        "repo_root": safe_path(repo_root),
        "interpretation_required": True,
        "records": evidence,
        "scan": scan,
    }

    environment_path = output_dir / "environment_probe.json"
    dependency_path = output_dir / "dependency_evidence.json"
    write_json(environment_path, environment_probe)
    write_json(dependency_path, dependency_evidence)
    write_verification_commands(output_dir)

    summary = {
        "status": "ok",
        "repo_root": safe_path(repo_root),
        "output_dir": safe_path(output_dir),
        "environment_probe": safe_path(environment_path),
        "dependency_evidence": safe_path(dependency_path),
        "dependency_records": len(evidence),
        "candidate_files_scanned": scan["candidate_files_scanned"],
        "scan_truncated": scan["truncated"],
        "interpretation_required": True,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(
            f"fatal: {type(exc).__name__}: {redact_text(str(exc))}",
            file=sys.stderr,
        )
        raise SystemExit(2)
