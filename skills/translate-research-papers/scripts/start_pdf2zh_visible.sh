#!/usr/bin/env bash
set -euo pipefail

server_directory="${PDF2ZH_SERVER_DIRECTORY:-}"
port=8890
wait_seconds=40

usage() {
  printf '%s\n' \
    'Usage: start_pdf2zh_visible.sh [--server-directory PATH] [--port PORT] [--wait-seconds SECONDS]' \
    '' \
    'Start the native-Linux PDF2zh server in a visible terminal and wait for /health.'
}

while (($#)); do
  case "$1" in
    --server-directory)
      server_directory=${2:?missing path after --server-directory}
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

if [[ -z "$server_directory" ]]; then
  for candidate in \
    "$HOME/resource/env/zotero/zotero-pdf2zh/server" \
    "$HOME/resource/env/fanyi/server/server"; do
    if [[ -f "$candidate/server.py" ]]; then
      server_directory=$candidate
      break
    fi
  done
fi

[[ -n "$server_directory" ]] || {
  printf 'PDF2zh server directory was not found; pass --server-directory.\n' >&2
  exit 1
}
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
if command -v uv >/dev/null 2>&1; then
  run_command=(uv run --python 3.12 --with-requirements requirements.txt server.py --port "$port")
  method="uv"
elif command -v conda >/dev/null 2>&1 && conda env list 2>/dev/null | awk '{print $1}' | grep -qx PDF2zh; then
  run_command=(conda run -n PDF2zh python server.py --enable_venv false --check_update false --port "$port")
  method="conda"
elif python3 -c 'import flask, toml, pypdf, fitz' >/dev/null 2>&1; then
  run_command=(python3 server.py --enable_venv false --check_update false --port "$port")
  method="python"
else
  printf 'Neither uv, the PDF2zh Conda environment, nor a compatible Python is available.\n' >&2
  exit 1
fi

terminal=()
if command -v gnome-terminal >/dev/null 2>&1 && [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
  terminal=(gnome-terminal --title='PDF2zh Server — keep open' --)
elif command -v xterm >/dev/null 2>&1 && [[ -n "${DISPLAY:-}" ]]; then
  terminal=(xterm -T 'PDF2zh Server — keep open' -e)
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
