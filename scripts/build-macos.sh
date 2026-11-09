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

APP="dist/Kelebek Sınav Sistemi.app"
[[ -d "$APP" ]] || { echo "Uygulama paketi üretilemedi: $APP"; exit 1; }

# Apple Silicon çekirdeği imzası olmayan ikili dosyayı çalıştırmaz. Paket, artımlı
# güncellemeden sonra da aynı biçimde yenilenebilsin diye burada açıkça ad-hoc
# imzalanır ve karantina damgaları temizlenir.
xattr -cr "$APP" || true
codesign --force --deep --sign - --timestamp=none "$APP"
codesign --verify --deep --strict "$APP" || { echo "Uygulama imzası doğrulanamadı."; exit 1; }

VERSION="$(PYTHONPATH=backend .venv/bin/python -c 'from kelebek.version import APP_VERSION;print(APP_VERSION)')"
DMG="dist/KelebekSinavSistemi-${VERSION}-macos-arm64.dmg"
rm -f "$DMG"
STAGE="$(mktemp -d)"
cp -R "dist/Kelebek Sınav Sistemi.app" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
for attempt in 1 2 3; do
  hdiutil create -volname "Kelebek Sınav Sistemi" -srcfolder "$STAGE" -ov -format UDZO "$DMG" && break
  echo "DMG oluşturma yeniden deneniyor ($attempt)…"; sleep 5
done
[[ -f "$DMG" ]] || { echo "DMG oluşturulamadı."; exit 1; }
rm -rf "$STAGE"
(cd dist && shasum -a 256 "$(basename "$DMG")" > "$(basename "$DMG").sha256")
echo "Hazır: $DMG"
