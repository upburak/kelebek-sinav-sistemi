#!/usr/bin/env bash
# Pardus / Debian tabanlı Linux (x64) için .deb ve .tar.gz üretir. Çıktı: dist/
#
# Paket, derlendiği sistemin glibc sürümünü ve daha yenisini ister. Pardus 21 ve 23'te
# çalışması için GitHub Actions bu betiği Debian 11 (glibc 2.31) kabında koşturur.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON=""
for candidate in python3.12 python3.13 python3.14 python3 python; do
  command -v "$candidate" >/dev/null 2>&1 || continue
  if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)' 2>/dev/null; then
    PYTHON="$candidate"; break
  fi
done
[[ -n "$PYTHON" ]] || { echo "Python 3.12 veya üzeri bulunamadı."; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Node.js bulunamadı. Önce Node.js 22.12 veya üzeri kurun."; exit 1; }
command -v dpkg-deb >/dev/null 2>&1 || { echo "dpkg-deb bulunamadı (dpkg paketi gerekli)."; exit 1; }

if [[ ! -x .venv/bin/python ]]; then
  "$PYTHON" -m venv .venv
  .venv/bin/python -m pip install --quiet --upgrade pip
  .venv/bin/python -m pip install --quiet -e .
fi
.venv/bin/python -m pip install --quiet "pyinstaller>=6.10,<7"
npm --prefix frontend ci
npm --prefix frontend run build

if [[ "${KELEBEK_SKIP_TESTS:-}" != "1" ]]; then
  PYTHONPATH=backend .venv/bin/python -m unittest discover -s backend/tests
fi
.venv/bin/python -m PyInstaller --noconfirm --clean --distpath dist --workpath build packaging/kelebek.spec

APP="dist/KelebekSinavSistemi"
[[ -x "$APP/KelebekSinavSistemi" ]] || { echo "Uygulama klasörü üretilemedi: $APP"; exit 1; }

VERSION="$(PYTHONPATH=backend .venv/bin/python -c 'from kelebek.version import APP_VERSION;print(APP_VERSION)')"
GLIBC="$(getconf GNU_LIBC_VERSION | awk '{print $2}')"
NAME="KelebekSinavSistemi-${VERSION}-linux-x64"

# Taşınabilir arşiv: açıp içindeki KelebekSinavSistemi dosyasını çalıştırmak yeterli.
rm -f "dist/${NAME}.tar.gz"
tar -C dist -czf "dist/${NAME}.tar.gz" --transform "s#^KelebekSinavSistemi#${NAME}#" KelebekSinavSistemi

# Debian paketi: /opt altına kurulur, uygulama menüsüne kısayol ekler.
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
PKG="$STAGE/pkg"
mkdir -p "$PKG/DEBIAN" "$PKG/opt" "$PKG/usr/bin" "$PKG/usr/share/applications" \
  "$PKG/usr/share/icons/hicolor/scalable/apps" "$PKG/usr/share/doc/kelebek-sinav-sistemi"
cp -R "$APP" "$PKG/opt/kelebek-sinav-sistemi"
ln -s /opt/kelebek-sinav-sistemi/KelebekSinavSistemi "$PKG/usr/bin/kelebek-sinav-sistemi"
cp packaging/linux/kelebek-sinav-sistemi.desktop "$PKG/usr/share/applications/"
cp packaging/icon/kelebek.svg "$PKG/usr/share/icons/hicolor/scalable/apps/kelebek-sinav-sistemi.svg"
cp CHANGELOG.md "$PKG/usr/share/doc/kelebek-sinav-sistemi/"
find "$PKG" -type d -exec chmod 755 {} +
find "$PKG" -type f -exec chmod u+rw,go+r,go-w {} +
SIZE_KB="$(du -sk "$PKG/opt" | cut -f1)"
cat > "$PKG/DEBIAN/control" <<CONTROL
Package: kelebek-sinav-sistemi
Version: ${VERSION}
Section: education
Priority: optional
Architecture: amd64
Depends: libc6 (>= ${GLIBC}), xdg-utils
Installed-Size: ${SIZE_KB}
Maintainer: Kelebek Sınav Sistemi <noreply@users.noreply.github.com>
Homepage: https://github.com/upburak/kelebek-sinav-sistemi
Description: Ortak sınavlar için kelebek oturma düzeni
 Öğrencileri dersliklere kurallara göre dağıtır; kroki, yoklama ve dağıtım
 listelerini üretir. İnternet gerektirmez; veriler bu bilgisayarda,
 kullanıcının ev dizininde tutulur ve güncellemede korunur.
CONTROL
cat > "$PKG/DEBIAN/postinst" <<'POSTINST'
#!/bin/sh
set -e
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database -q /usr/share/applications || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
exit 0
POSTINST
cp "$PKG/DEBIAN/postinst" "$PKG/DEBIAN/postrm"
chmod 755 "$PKG/DEBIAN/postinst" "$PKG/DEBIAN/postrm"

DEB="dist/${NAME}.deb"
rm -f "$DEB"
# xz: Pardus 21'in (Debian 11) dpkg sürümü zstd sıkıştırmalı paketi açamaz.
dpkg-deb --root-owner-group -Zxz --build "$PKG" "$DEB" >/dev/null
(cd dist && sha256sum "${NAME}.deb" "${NAME}.tar.gz" > SHA256SUMS-linux.txt)
echo "Hazır: $DEB (glibc >= ${GLIBC})"
echo "Hazır: dist/${NAME}.tar.gz"
