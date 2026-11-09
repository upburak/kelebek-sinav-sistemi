#!/usr/bin/env python3
"""İki paketlenmiş sürümü karşılaştırıp yalnızca değişen dosyaları içeren güncelleme paketi üretir.

Kullanım:
  python scripts/make_update_package.py --old "eski/Kelebek Sınav Sistemi.app" --new "dist/Kelebek Sınav Sistemi.app" \
      --platform macos-arm64 --from-version 0.2.0 --to-version 0.3.0 --out dist
Windows'ta --old/--new olarak KelebekSinavSistemi klasörlerini verin.
"""

import argparse
import hashlib
import json
import re
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import update_signing

FORMAT = "kelebek-update/1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan(root: Path) -> dict[str, Path]:
    return {path.relative_to(root).as_posix(): path for path in root.rglob("*") if path.is_file() and not path.is_symlink()}


def head_revision(root: Path) -> str | None:
    versions = [path for path in root.rglob("migrations/versions/*.py")]
    revisions, parents = set(), set()
    for path in versions:
        text = path.read_text(encoding="utf-8")
        revision = re.search(r'^revision\s*=\s*"([^"]+)"', text, re.M)
        parent = re.search(r'^down_revision\s*=\s*"([^"]+)"', text, re.M)
        if revision:
            revisions.add(revision.group(1))
        if parent:
            parents.add(parent.group(1))
    heads = sorted(revisions - parents)
    return heads[-1] if heads else None


def build(old: Path, new: Path, platform: str, from_version: str, to_version: str, out: Path, notes: str = "",
          sign_key: Path | None = None) -> Path:
    old_files, new_files = scan(old), scan(new)
    changed = [rel for rel, path in sorted(new_files.items())
               if rel not in old_files or old_files[rel].stat().st_size != path.stat().st_size or sha256(old_files[rel]) != sha256(path)]
    removed = sorted(set(old_files) - set(new_files))
    from_revision, to_revision = head_revision(old), head_revision(new)
    manifest = {
        "format": FORMAT, "from_version": from_version, "to_version": to_version, "platform": platform,
        "created_at": datetime.now(UTC).isoformat(), "notes": notes,
        "min_app_version": from_version,
        "migrations": {"required": from_revision != to_revision, "from_revision": from_revision, "to_revision": to_revision},
        "files": [{"path": rel, "size": new_files[rel].stat().st_size, "sha256": sha256(new_files[rel]),
                   "mode": new_files[rel].stat().st_mode & 0o777} for rel in changed],
        "removed": removed,
    }
    sign_key = sign_key or update_signing.DEFAULT_KEY
    if not sign_key.is_file():
        raise SystemExit(f"İmzalama anahtarı bulunamadı: {sign_key}. Önce 'python scripts/update_signing.py init' çalıştırın.")
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"KelebekSinavSistemi-update-{from_version}-to-{to_version}-{platform}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as package:
        package.writestr("manifest.json", manifest_bytes)
        package.writestr("manifest.sig", update_signing.sign(sign_key, manifest_bytes))
        for rel in changed:
            package.write(new_files[rel], f"files/{rel}")
    (target.parent / f"{target.name}.sha256").write_text(f"{sha256(target)}  {target.name}\n", encoding="utf-8")
    print(f"{len(changed)} değişen, {len(removed)} kaldırılan dosya → {target}")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--old", required=True, type=Path)
    parser.add_argument("--new", required=True, type=Path)
    parser.add_argument("--platform", required=True, choices=["macos-arm64", "macos-x64", "windows-x64", "windows-arm64", "linux-x64", "linux-arm64"])
    parser.add_argument("--from-version", required=True)
    parser.add_argument("--to-version", required=True)
    parser.add_argument("--out", default=Path("dist"), type=Path)
    parser.add_argument("--notes", default="")
    parser.add_argument("--sign-key", type=Path, default=None, help="Ed25519 gizli anahtar (varsayılan ~/.kelebek-signing/...)")
    args = parser.parse_args()
    build(args.old, args.new, args.platform, args.from_version, args.to_version, args.out, args.notes, args.sign_key)


if __name__ == "__main__":
    main()
