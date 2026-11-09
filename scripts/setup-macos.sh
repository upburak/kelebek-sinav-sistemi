#!/usr/bin/env bash
# macOS geliştirme ortamı: Python 3.12 veya üzeri bir sürümle .venv kurar.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# pyproject ">=3.12" istediği için 3.12'yi tercih edip daha yeni sürümleri de kabul et.
PYTHON=""
for candidate in python3.14 python3.13 python3.12 python3 python; do
  command -v "$candidate" >/dev/null 2>&1 || continue
  if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)' 2>/dev/null; then
    PYTHON="$candidate"
    break
  fi
done
# 3.12 kuruluysa onu kullan; sürüm farklarından kaynaklanan sürprizleri azaltır.
if command -v python3.12 >/dev/null 2>&1; then PYTHON="python3.12"; fi
if [[ -z "$PYTHON" ]]; then
  echo "Python 3.12 veya üzeri bulunamadı. Önce Python 3.12+ kurun."
  exit 1
fi
if ! command -v node >/dev/null 2>&1; then
  echo "Node.js bulunamadı. Önce Node.js 22.12 veya üzeri kurun."
  exit 1
fi

echo "Kullanılan Python: $("$PYTHON" -c 'import sys;print(sys.executable, sys.version.split()[0])')"
"$PYTHON" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
npm --prefix frontend install

echo "Kurulum tamamlandı. Geliştirmeyi başlatmak için ./scripts/dev-macos.sh çalıştırın."
