#!/usr/bin/env bash
# Apple Silicon macOS için .app ve DMG üretir. Çıktı: dist/
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -x .venv/bin/python ]]; then ./scripts/setup-macos.sh; fi
.venv/bin/python -m pip install --quiet "pyinstaller>=6.10,<7"
npm --prefix frontend ci
npm --prefix frontend run build

PYTHONPATH=backend .venv/bin/python -m unittest discover -s backend/tests
.venv/bin/python -m PyInstaller --noconfirm --clean --distpath dist --workpath build packaging/kelebek.spec

VERSION="$(.venv/bin/python -c 'import tomllib;print(tomllib.load(open("pyproject.toml","rb"))["project"]["version"])')"
DMG="dist/KelebekSinavSistemi-${VERSION}-macos-arm64.dmg"
rm -f "$DMG"
STAGE="$(mktemp -d)"
cp -R "dist/Kelebek Sınav Sistemi.app" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
hdiutil create -volname "Kelebek Sınav Sistemi" -srcfolder "$STAGE" -ov -format UDZO "$DMG"
rm -rf "$STAGE"
(cd dist && shasum -a 256 "$(basename "$DMG")" > "$(basename "$DMG").sha256")
echo "Hazır: $DMG"
