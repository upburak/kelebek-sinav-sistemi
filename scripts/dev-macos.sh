#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "Önce ./scripts/setup-macos.sh çalıştırın."
  exit 1
fi

export PYTHONPATH="$ROOT/backend${PYTHONPATH:+:$PYTHONPATH}"
API_PORT="$("$PYTHON" "$ROOT/scripts/choose_api_port.py")"
UI_PORT="${KELEBEK_UI_PORT:-5173}"
export KELEBEK_API_PROXY_TARGET="http://127.0.0.1:${API_PORT}"
echo "Kelebek API: http://127.0.0.1:${API_PORT}"
echo "Kelebek arayüzü: http://127.0.0.1:${UI_PORT}"
"$PYTHON" -m flask --app kelebek:create_app run --host 127.0.0.1 --port "$API_PORT" &
BACKEND_PID=$!
cleanup() { kill "$BACKEND_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

cd "$ROOT/frontend"
npm run dev -- --host 127.0.0.1 --port "$UI_PORT" --strictPort
