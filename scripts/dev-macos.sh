#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "Önce ./scripts/setup-macos.sh çalıştırın."
  exit 1
fi

export PYTHONPATH="$ROOT/backend${PYTHONPATH:+:$PYTHONPATH}"
export KELEBEK_DATA_DIR="$ROOT/.local-data"
"$PYTHON" -m flask --app kelebek:create_app run --host 127.0.0.1 --port 5000 &
BACKEND_PID=$!
cleanup() { kill "$BACKEND_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

cd "$ROOT/frontend"
npm run dev -- --host 127.0.0.1
