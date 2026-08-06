#!/usr/bin/env bash
set -euo pipefail

script_directory=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
server_directory="${PDF2ZH_SERVER_DIRECTORY:-}"
config_path="${PDF2ZH_SKILL_CONFIG:-}"
search_root=""
port=8890
wait_seconds=40

usage() {
  printf '%s\n' \
    'Usage: start_pdf2zh_visible.sh [--server-directory PATH] [--config PATH] [--search-root PATH] [--port PORT] [--wait-seconds SECONDS]' \
    '' \
    'Refresh local path discovery, start PDF2zh visibly, and wait for /health.'
}

while (($#)); do
  case "$1" in
    --server-directory)
      server_directory=${2:?missing path after --server-directory}
      shift 2
      ;;
    --config)
      config_path=${2:?missing path after --config}
      shift 2
      ;;
    --search-root)
      search_root=${2:?missing path after --search-root}
      shift 2
      ;;
    --port)
      port=${2:?missing value after --port}
      shift 2
      ;;
    --wait-seconds)
      wait_seconds=${2:?missing value after --wait-seconds}
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

[[ "$port" =~ ^[0-9]+$ ]] || { printf 'Port must be numeric.\n' >&2; exit 2; }
[[ "$wait_seconds" =~ ^[0-9]+$ ]] || { printf 'Wait time must be numeric.\n' >&2; exit 2; }

resolver_python=$(command -v python3 || command -v python || true)
[[ -n "$resolver_python" ]] || {
  printf 'Python is required to discover and cache local PDF2zh paths.\n' >&2
  exit 1
}
resolver=("$resolver_python" "$script_directory/local_config.py")
refresh=("${resolver[@]}" refresh)
[[ -z "$config_path" ]] || refresh+=(--config "$config_path")
[[ -z "$server_directory" ]] || refresh+=(--server-directory "$server_directory")
[[ -z "$search_root" ]] || refresh+=(--search-root "$search_root")
"${refresh[@]}" >/dev/null

config_get() {
  local key=$1
  local command=("${resolver[@]}" get "$key")
  [[ -z "$config_path" ]] || command+=(--config "$config_path")
  "${command[@]}"
}

server_directory=$(config_get pdf2zh_server_directory)

server_directory=$(realpath "$server_directory")
[[ -f "$server_directory/server.py" ]] || {
  printf 'server.py not found below %s\n' "$server_directory" >&2
  exit 1
}
[[ -f "$server_directory/requirements.txt" ]] || {
  printf 'requirements.txt not found below %s\n' "$server_directory" >&2
  exit 1
}

health_url="http://127.0.0.1:${port}/health"
if curl -fsS --connect-timeout 2 "$health_url" >/dev/null 2>&1; then
  if command -v ss >/dev/null 2>&1; then
    listener_pid=$(ss -ltnp "( sport = :${port} )" 2>/dev/null |
      sed -n 's/.*pid=\([0-9][0-9]*\).*/\1/p' | head -1)
    if [[ -n "$listener_pid" && -r "/proc/${listener_pid}/environ" ]] &&
      tr '\0' '\n' < "/proc/${listener_pid}/environ" |
        grep -Eiq '^(ALL_PROXY|all_proxy)=socks://'; then
      printf '%s\n' \
        'PDF2zh is listening but inherited unsupported ALL_PROXY=socks://…' \
        'Stop only this PDF2zh server process and rerun this launcher.' >&2
      exit 1
    fi
  fi
  printf '{"status":"already-running","port":%s,"method":"existing"}\n' "$port"
  exit 0
fi

run_command=()
method=""
uv_executable=$(config_get uv_executable 2>/dev/null || true)
conda_executable=$(config_get conda_executable 2>/dev/null || true)
python_executable=$(config_get python_executable 2>/dev/null || true)
if [[ -n "$uv_executable" ]]; then
  run_command=("$uv_executable" run --python 3.12 --with-requirements requirements.txt server.py --port "$port")
  method="uv"
elif [[ -n "$conda_executable" ]] && "$conda_executable" env list 2>/dev/null | awk '{print $1}' | grep -qx PDF2zh; then
  run_command=("$conda_executable" run -n PDF2zh python server.py --enable_venv false --check_update false --port "$port")
  method="conda"
elif [[ -n "$python_executable" ]] && "$python_executable" -c 'import flask, toml, pypdf, fitz' >/dev/null 2>&1; then
  run_command=("$python_executable" server.py --enable_venv false --check_update false --port "$port")
  method="python"
else
  printf 'Neither uv, the PDF2zh Conda environment, nor a compatible Python is available.\n' >&2
  exit 1
fi

terminal=()
terminal_executable=$(config_get terminal_executable 2>/dev/null || true)
terminal_name=$(basename -- "${terminal_executable:-missing}")
if [[ "$terminal_name" == "gnome-terminal" && -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
  terminal=("$terminal_executable" --title='PDF2zh Server — keep open' --)
elif [[ "$terminal_name" == "xterm" && -n "${DISPLAY:-}" ]]; then
  terminal=("$terminal_executable" -T 'PDF2zh Server — keep open' -e)
elif [[ "$terminal_name" == "konsole" && -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
  terminal=("$terminal_executable" --new-tab -p tabtitle='PDF2zh Server — keep open' -e)
elif [[ "$terminal_name" == "xfce4-terminal" && -n "${DISPLAY:-}" ]]; then
  terminal=("$terminal_executable" --title='PDF2zh Server — keep open' --execute)
else
  printf 'No graphical terminal is available; start the server visibly before continuing.\n' >&2
  exit 1
fi

"${terminal[@]}" bash -lc '
  cd -- "$1"
  shift
  for proxy_name in ALL_PROXY all_proxy; do
    if [[ "$proxy_name" == "ALL_PROXY" ]]; then
      proxy_value=${ALL_PROXY:-}
    else
      proxy_value=${all_proxy:-}
    fi
    if [[ "$proxy_value" == socks://* ]]; then
      unset "$proxy_name"
      printf "Removed unsupported %s=socks://… for PDF2zh; HTTP(S) proxy variables are unchanged.\n" "$proxy_name"
    fi
  done
  export PYTHONIOENCODING=utf-8
  export PATH="$PWD/zotero-pdf2zh-venv/bin:$PWD/zotero-pdf2zh-next-venv/bin:$PATH"
  "$@"
  status=$?
  printf "\nPDF2zh server exited with status %s. This terminal remains open for diagnostics.\n" "$status"
  exec bash
' bash "$server_directory" "${run_command[@]}"

deadline=$((SECONDS + wait_seconds))
while ((SECONDS < deadline)); do
  if curl -fsS --connect-timeout 2 "$health_url" >/dev/null 2>&1; then
    printf '{"status":"started","port":%s,"method":"%s"}\n' "$port" "$method"
    exit 0
  fi
  sleep 1
done

printf 'PDF2zh did not become healthy within %s seconds; inspect the visible terminal.\n' "$wait_seconds" >&2
exit 1
