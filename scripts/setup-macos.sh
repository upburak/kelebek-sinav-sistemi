#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v python3.12 >/dev/null 2>&1; then
  echo "Python 3.12 bulunamadı. Önce Python 3.12 kurun."
  exit 1
fi
if ! command -v node >/dev/null 2>&1; then
  echo "Node.js bulunamadı. Önce Node.js 22.12 veya üzeri kurun."
  exit 1
fi

python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
npm --prefix frontend install

echo "Kurulum tamamlandı. Geliştirmeyi başlatmak için ./scripts/dev-macos.sh çalıştırın."
