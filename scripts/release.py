#!/usr/bin/env python3
"""Tek komutla sürüm: sürüm numarası + notlar → testler, tam kurulum paketi ve imzalı güncelleme paketi.

  macOS:   .venv/bin/python scripts/release.py --version 0.3.0 --notes "Yeni özellik" --notes "Düzeltme"
  Windows: .venv\\Scripts\\python.exe scripts\\release.py --version 0.3.0 --notes "Yeni özellik"

Her sürümün uygulama klasörü releases/<platform>/<sürüm>/ altında saklanır; bir sonraki sürümde
güncelleme paketi bu kopyayla karşılaştırılarak üretilir. releases/ klasörünü silmeyin (Git'e girmez).
"""

import argparse
import json
import platform as platform_module
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "backend"))
import make_update_package  # noqa: E402
import update_signing  # noqa: E402

VERSION_FILE = ROOT / "backend" / "kelebek" / "version.py"
NOTES_FILE = ROOT / "backend" / "kelebek" / "release_notes.py"
PYPROJECT = ROOT / "pyproject.toml"
RELEASES = ROOT / "releases"


def parse(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", value)
    if not match:
        raise SystemExit(f"Sürüm MAJOR.MINOR.PATCH biçiminde olmalı: {value}")
    return tuple(int(part) for part in match.groups())


def current_version() -> str:
    return re.search(r'APP_VERSION = "([^"]+)"', VERSION_FILE.read_text(encoding="utf-8")).group(1)


def platform_id() -> str:
    arch = "arm64" if platform_module.machine().lower() in {"arm64", "aarch64"} else "x64"
    return {"darwin": "macos", "win32": "windows"}.get(sys.platform, "linux") + f"-{arch}"


def app_root() -> Path:
    if sys.platform == "darwin":
        return ROOT / "dist" / "Kelebek Sınav Sistemi.app"
    return ROOT / "dist" / "KelebekSinavSistemi"


def write_version(version: str, notes: list[str]) -> None:
    VERSION_FILE.write_text(re.sub(r'APP_VERSION = "[^"]+"', f'APP_VERSION = "{version}"', VERSION_FILE.read_text(encoding="utf-8")), encoding="utf-8")
    PYPROJECT.write_text(re.sub(r'(?m)^version = "[^"]+"', f'version = "{version}"', PYPROJECT.read_text(encoding="utf-8"), count=1), encoding="utf-8")
    text = NOTES_FILE.read_text(encoding="utf-8")
    header, body = text.split("RELEASE_NOTES = ", 1)
    entries = [item for item in json.loads(body) if item["version"] != version]
    entries.insert(0, {"version": version, "date": date.today().isoformat(), "items": notes})
    NOTES_FILE.write_text(f"{header}RELEASE_NOTES = {json.dumps(entries, ensure_ascii=False, indent=2)}\n", encoding="utf-8")


def previous_release(platform: str, version: str) -> tuple[str, Path] | None:
    folder = RELEASES / platform
    versions = sorted((item.name for item in folder.iterdir() if item.is_dir() and re.fullmatch(r"\d+\.\d+\.\d+", item.name)
                       and parse(item.name) < parse(version)), key=parse) if folder.is_dir() else []
    if not versions:
        return None
    previous = versions[-1]
    return previous, folder / previous / app_root().name


def check_signing(key: Path) -> None:
    from kelebek import update_trust

    if not key.is_file():
        raise SystemExit(f"İmzalama anahtarı yok: {key}\nÖnce bir kez 'python scripts/update_signing.py init' çalıştırın.")
    public = update_signing.public_key_b64(update_signing.load_private_key(key))
    if public not in update_trust.TRUSTED_PUBLIC_KEYS:
        raise SystemExit("İmzalama anahtarınız uygulamada güvenilir anahtar olarak tanımlı değil. "
                         "'python scripts/update_signing.py init' çalıştırıp tekrar deneyin.")


def build() -> None:
    if sys.platform == "win32":
        command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "scripts" / "build-windows.ps1")]
    elif sys.platform == "darwin":
        command = ["bash", str(ROOT / "scripts" / "build-macos.sh")]
    else:
        raise SystemExit("Paketler yalnızca macOS veya Windows üzerinde üretilir.")
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", required=True)
    parser.add_argument("--notes", action="append", default=[], help="Yenilikler maddesi (birden çok kez verilebilir)")
    parser.add_argument("--sign-key", type=Path, default=update_signing.DEFAULT_KEY)
    parser.add_argument("--skip-build", action="store_true", help="dist/ içindeki hazır paketi kullan")
    args = parser.parse_args()

    old = current_version()
    if parse(args.version) <= parse(old):
        raise SystemExit(f"Yeni sürüm ({args.version}) mevcut sürümden ({old}) büyük olmalı.")
    if not args.notes:
        raise SystemExit("En az bir --notes maddesi girin; kullanıcı güncellemeden sonra bu notları görür.")
    check_signing(args.sign_key)
    platform = platform_id()
    write_version(args.version, args.notes)
    print(f"Sürüm {old} → {args.version} ({platform}) hazırlanıyor…")
    if not args.skip_build:
        build()
    root = app_root()
    if not root.exists():
        raise SystemExit(f"Paketlenmiş uygulama bulunamadı: {root}")
    outputs = [path.name for path in (ROOT / "dist").iterdir() if path.is_file() and args.version in path.name]
    previous = previous_release(platform, args.version)
    if previous and previous[1].exists():
        package = make_update_package.build(previous[1], root, platform, previous[0], args.version, ROOT / "dist",
                                            "\n".join(args.notes), args.sign_key)
        outputs += [package.name, f"{package.name}.sha256"]
    else:
        print("Önceki sürüm kopyası bulunamadı; bu sürüm için yalnızca tam kurulum paketi üretildi.")
    target = RELEASES / platform / args.version
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    shutil.copytree(root, target / root.name, symlinks=True)
    print("\nYayın dosyaları (dist/):")
    for name in sorted(set(outputs)):
        print(f"  • {name}")
    print(f"\nSonraki sürümün güncelleme paketi için bu sürüm saklandı: {target}")
    print("Değişen sürüm ve not dosyalarını kaydedin (Save to GitHub).")


if __name__ == "__main__":
    main()
