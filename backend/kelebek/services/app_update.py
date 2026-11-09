"""Artımlı güncelleme: paket doğrulama, hazırlama ve dış güncelleyiciyle güvenli uygulama.

Akış (Teknik Mimari 11.3): sürüm kontrolü → özet → güvenlik yedeği → geçici dizinde hash
doğrulaması → uygulama kapanır, dış betik dosyaları değiştirir → yeni sürüm migration ve sağlık
kontrolünü geçerse etkin kalır; geçemezse önceki dosyalar ve veritabanı kopyası geri yüklenir.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from kelebek import update_trust
from kelebek.config import get_data_dir, get_database_path
from kelebek.version import APP_VERSION

MANIFEST_NAME = "manifest.json"
SIGNATURE_NAME = "manifest.sig"
FORMAT = "kelebek-update/1"
MAX_PACKAGE_BYTES = 600 * 1024 * 1024
VERIFY_TIMEOUT_SECONDS = 120


class UpdateError(ValueError):
    pass


def current_platform() -> str:
    machine = platform.machine().lower()
    arch = "arm64" if machine in {"arm64", "aarch64"} else "x64"
    if sys.platform == "darwin":
        return f"macos-{arch}"
    if sys.platform == "win32":
        return f"windows-{arch}"
    return f"linux-{arch}"


def install_root() -> Path | None:
    """Paketlenmiş uygulamanın kök klasörü (.app veya Windows kurulum klasörü)."""
    override = os.environ.get("KELEBEK_INSTALL_ROOT")
    if override:
        return Path(override)
    if not getattr(sys, "frozen", False):
        return None
    executable = Path(sys.executable).resolve()
    if sys.platform == "darwin" and executable.parent.name == "MacOS":
        return executable.parents[2]
    return executable.parent


def _updates_dir() -> Path:
    path = get_data_dir() / "updates"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative(value) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise UpdateError("Güncelleme paketinde geçersiz bir dosya yolu var.")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.parts[0] in {"", "."}:
        raise UpdateError("Güncelleme paketinde uygulama klasörü dışına çıkan bir dosya yolu var.")
    return str(path)


def _validate_manifest(manifest: dict) -> dict:
    if not isinstance(manifest, dict) or manifest.get("format") != FORMAT:
        raise UpdateError("Bu dosya Kelebek güncelleme paketi değil.")
    for key in ("from_version", "to_version", "platform"):
        if not isinstance(manifest.get(key), str) or not manifest[key]:
            raise UpdateError("Güncelleme paketinin sürüm bilgileri eksik.")
    files = manifest.get("files")
    removed = manifest.get("removed", [])
    if not isinstance(files, list) or not isinstance(removed, list):
        raise UpdateError("Güncelleme paketinin dosya listesi geçersiz.")
    for item in files:
        if not isinstance(item, dict) or not isinstance(item.get("sha256"), str) or not isinstance(item.get("size"), int):
            raise UpdateError("Güncelleme paketinin dosya listesi geçersiz.")
        item["path"] = _safe_relative(item.get("path"))
    manifest["removed"] = [_safe_relative(item) for item in removed]
    return manifest


def _summary(manifest: dict, package_sha256: str) -> dict:
    migrations = manifest.get("migrations") or {}
    return {
        "from_version": manifest["from_version"], "to_version": manifest["to_version"],
        "platform": manifest["platform"], "changed_file_count": len(manifest["files"]),
        "removed_file_count": len(manifest["removed"]),
        "changed_bytes": sum(item["size"] for item in manifest["files"]),
        "migration_required": bool(migrations.get("required")),
        "migration_from": migrations.get("from_revision"), "migration_to": migrations.get("to_revision"),
        "notes": str(manifest.get("notes", ""))[:2000],
        "package_sha256": package_sha256, "created_at": manifest.get("created_at"),
    }


def inspect_package(stream: BinaryIO) -> tuple[str, dict]:
    """Paketi geçici dizine al, manifest ve her dosyanın SHA-256 değerini doğrula."""
    token = uuid.uuid4().hex
    staged_root = _updates_dir() / "staged"
    if staged_root.is_dir():
        cutoff = datetime.now(timezone.utc).timestamp() - 24 * 3600
        for old in staged_root.iterdir():
            if old.is_dir() and old.stat().st_mtime < cutoff:
                shutil.rmtree(old, ignore_errors=True)
    stage = staged_root / token
    stage.mkdir(parents=True)
    archive = stage / "package.zip"
    try:
        with archive.open("wb") as handle:
            shutil.copyfileobj(stream, handle, 1024 * 1024)
        if archive.stat().st_size > MAX_PACKAGE_BYTES:
            raise UpdateError("Güncelleme paketi beklenenden büyük.")
        package_sha256 = _sha256_file(archive)
        with zipfile.ZipFile(archive) as package:
            try:
                manifest_bytes = package.read(MANIFEST_NAME)
            except KeyError:
                raise UpdateError("Güncelleme paketinde manifest bulunamadı.") from None
            key_id = verify_signature(manifest_bytes, package)
            manifest = _validate_manifest(json.loads(manifest_bytes))
            if manifest["platform"] != current_platform():
                raise UpdateError(f"Bu paket {manifest['platform']} içindir; bu bilgisayar {current_platform()}.")
            if manifest["from_version"] != APP_VERSION:
                raise UpdateError(f"Bu paket {manifest['from_version']} sürümünden günceller; kurulu sürüm {APP_VERSION}.")
            files_dir = stage / "files"
            for item in manifest["files"]:
                target = files_dir / item["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                try:
                    with package.open(f"files/{item['path']}") as source, target.open("wb") as handle:
                        shutil.copyfileobj(source, handle, 1024 * 1024)
                except KeyError:
                    raise UpdateError(f"Pakette eksik dosya: {item['path']}") from None
                if target.stat().st_size != item["size"] or _sha256_file(target) != item["sha256"]:
                    raise UpdateError(f"Dosya doğrulaması başarısız: {item['path']}")
                mode = item.get("mode")
                if isinstance(mode, int) and os.name != "nt":
                    target.chmod(mode & 0o755)
        archive.unlink()
        (stage / MANIFEST_NAME).write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        (stage / "files.txt").write_text("".join(f"{item['path']}\n" for item in manifest["files"]), encoding="utf-8")
        (stage / "removed.txt").write_text("".join(f"{item}\n" for item in manifest["removed"]), encoding="utf-8")
    except (UpdateError, zipfile.BadZipFile, json.JSONDecodeError, OSError) as error:
        shutil.rmtree(stage, ignore_errors=True)
        if isinstance(error, UpdateError):
            raise
        raise UpdateError("Güncelleme paketi açılamadı veya bozuk.") from error
    return token, {**_summary(manifest, package_sha256), "signature_key_id": key_id}


def _key_id(public_b64: str) -> str:
    return hashlib.sha256(base64.b64decode(public_b64)).hexdigest()[:16]


def verify_signature(manifest_bytes: bytes, package: zipfile.ZipFile) -> str:
    """Manifest, tüm dosyaların SHA-256 değerlerini taşır; manifest imzası tüm paketi bağlar."""
    trusted = list(update_trust.TRUSTED_PUBLIC_KEYS)
    if not trusted:
        raise UpdateError("Bu kurulumda güvenilir yayıncı anahtarı tanımlı değil; güncelleme kabul edilmiyor. Tam kurulum paketini kullanın.")
    try:
        signature = base64.b64decode(package.read(SIGNATURE_NAME).strip(), validate=True)
    except KeyError:
        raise UpdateError("Paket imzasız. Yalnızca yayıncı anahtarınızla imzalanmış güncellemeler kabul edilir.") from None
    except ValueError:
        raise UpdateError("Paket imzası okunamadı.") from None
    for public_b64 in trusted:
        try:
            Ed25519PublicKey.from_public_bytes(base64.b64decode(public_b64)).verify(signature, manifest_bytes)
            return _key_id(public_b64)
        except (InvalidSignature, ValueError):
            continue
    raise UpdateError("İmza doğrulanamadı: paket sizin yayıncı anahtarınızla imzalanmamış veya değiştirilmiş.")


def _stage_dir(token) -> Path:
    if not isinstance(token, str) or len(token) != 32 or not token.isalnum():
        raise UpdateError("Güncelleme önizlemesi bulunamadı; paketi yeniden seçin.")
    stage = _updates_dir() / "staged" / token
    if not (stage / MANIFEST_NAME).is_file():
        raise UpdateError("Güncelleme önizlemesi bulunamadı; paketi yeniden seçin.")
    return stage


def discard(token) -> bool:
    try:
        shutil.rmtree(_stage_dir(token))
        return True
    except UpdateError:
        return False


def last_result() -> dict | None:
    path = _updates_dir() / "last_result.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def status() -> dict:
    root = install_root()
    return {"current_version": APP_VERSION, "platform": current_platform(),
            "can_apply": root is not None, "last_result": last_result(),
            "trusted_key_ids": [_key_id(item) for item in update_trust.TRUSTED_PUBLIC_KEYS]}


def _launch_command(root: Path) -> list[str]:
    if sys.platform == "darwin" and root.suffix == ".app":
        return [str(root / "Contents" / "MacOS" / "KelebekSinavSistemi")]
    if sys.platform == "win32":
        return [str(root / "KelebekSinavSistemi.exe")]
    return [str(root / "KelebekSinavSistemi")]


def prepare_apply(token, safety_backup: Path) -> dict:
    """Dış güncelleyici için iş tanımını yaz; uygulama kapandıktan sonra betik çalışır."""
    root = install_root()
    if root is None:
        raise UpdateError("Güncelleme yalnızca kurulu (paketlenmiş) uygulamada uygulanabilir.")
    stage = _stage_dir(token)
    manifest = json.loads((stage / MANIFEST_NAME).read_text(encoding="utf-8"))
    job = {
        "app_pid": os.getpid(), "app_root": str(root), "staged": str(stage),
        "rollback": str(_updates_dir() / "rollback"), "db_path": str(get_database_path()),
        "launch": _launch_command(root), "verify_file": str(stage / "verified.txt"),
        "result_file": str(_updates_dir() / "last_result.json"), "log_file": str(_updates_dir() / "update.log"),
        "from_version": manifest["from_version"], "to_version": manifest["to_version"],
        "safety_backup": str(safety_backup), "timeout": VERIFY_TIMEOUT_SECONDS,
    }
    (stage / "job.json").write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
    env_lines = [f"{key.upper()}={shlex.quote(str(value))}" for key, value in job.items() if key != "launch"]
    env_lines.append(f"LAUNCH={shlex.quote(job['launch'][0])}")
    (stage / "job.env").write_text("\n".join(env_lines) + "\n", encoding="utf-8")
    return job


def spawn_updater(job: dict) -> None:
    stage = Path(job["staged"])
    if sys.platform == "win32":
        script = stage / "apply-update.ps1"
        script.write_text(WINDOWS_SCRIPT, encoding="utf-8-sig")
        flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        subprocess.Popen(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden",
                          "-File", str(script), "-Job", str(stage / "job.json")], creationflags=flags, close_fds=True)
        return
    script = stage / "apply-update.sh"
    script.write_text(POSIX_SCRIPT, encoding="utf-8")
    script.chmod(0o700)
    subprocess.Popen(["/bin/bash", str(script), str(stage / "job.env")], start_new_session=True, close_fds=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def write_verification(path: str) -> None:
    """Yeni sürüm migration'ları uygulayıp servisi açtıysa güncelleyiciye başarı bildir."""
    Path(path).write_text(f"ok {APP_VERSION} {datetime.now(timezone.utc).isoformat()}\n", encoding="utf-8")


POSIX_SCRIPT = r'''#!/bin/bash
# Kelebek artımlı güncelleyici (macOS/Linux). Uygulama kapandıktan sonra çalışır.
set -u
source "$1"
exec >>"$LOG_FILE" 2>&1
echo "=== $(date) $FROM_VERSION -> $TO_VERSION"
result() { printf '{"status":"%s","from_version":"%s","to_version":"%s","finished_at":"%s","message":"%s","safety_backup":"%s"}\n' "$1" "$FROM_VERSION" "$TO_VERSION" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$2" "$SAFETY_BACKUP" > "$RESULT_FILE"; }
for _ in $(seq 1 240); do kill -0 "$APP_PID" 2>/dev/null || break; sleep 0.5; done
if kill -0 "$APP_PID" 2>/dev/null; then result failed "Uygulama kapanmadı; güncelleme uygulanmadı."; exit 1; fi
rm -rf "$ROLLBACK"; mkdir -p "$ROLLBACK/files"; : > "$ROLLBACK/new.txt"
while IFS= read -r rel; do
  [ -z "$rel" ] && continue
  if [ -e "$APP_ROOT/$rel" ]; then mkdir -p "$ROLLBACK/files/$(dirname "$rel")"; cp -p "$APP_ROOT/$rel" "$ROLLBACK/files/$rel" || { result failed "Önceki dosyalar yedeklenemedi."; exit 1; }
  else echo "$rel" >> "$ROLLBACK/new.txt"; fi
done < <(cat "$STAGED/files.txt" "$STAGED/removed.txt")
for suffix in "" "-wal" "-shm"; do [ -f "$DB_PATH$suffix" ] && cp -p "$DB_PATH$suffix" "$ROLLBACK/db$suffix"; done
restore() {
  while IFS= read -r rel; do [ -n "$rel" ] && rm -f "$APP_ROOT/$rel"; done < "$ROLLBACK/new.txt"
  (cd "$ROLLBACK/files" && find . -type f -print0) | while IFS= read -r -d '' rel; do mkdir -p "$APP_ROOT/$(dirname "$rel")"; cp -p "$ROLLBACK/files/$rel" "$APP_ROOT/$rel"; done
  for suffix in "" "-wal" "-shm"; do rm -f "$DB_PATH$suffix"; [ -f "$ROLLBACK/db$suffix" ] && cp -p "$ROLLBACK/db$suffix" "$DB_PATH$suffix"; done
}
failed=0
while IFS= read -r rel; do
  [ -z "$rel" ] && continue
  mkdir -p "$APP_ROOT/$(dirname "$rel")" && cp -p "$STAGED/files/$rel" "$APP_ROOT/$rel" || { failed=1; break; }
done < "$STAGED/files.txt"
if [ "$failed" = 0 ]; then while IFS= read -r rel; do [ -n "$rel" ] && rm -f "$APP_ROOT/$rel"; done < "$STAGED/removed.txt"; fi
if [ "$failed" = 1 ]; then restore; result rolled_back "Dosyalar kopyalanamadı; önceki sürüm geri yüklendi."; "$LAUNCH" & exit 1; fi
rm -f "$VERIFY_FILE"
KELEBEK_UPDATE_VERIFY="$VERIFY_FILE" "$LAUNCH" &
NEW_PID=$!
for _ in $(seq 1 "$((TIMEOUT * 2))"); do
  [ -s "$VERIFY_FILE" ] && break
  kill -0 "$NEW_PID" 2>/dev/null || break
  sleep 0.5
done
if [ -s "$VERIFY_FILE" ]; then
  result success "Güncelleme tamamlandı."
  rm -rf "$STAGED/files"
  exit 0
fi
kill "$NEW_PID" 2>/dev/null; sleep 1; kill -9 "$NEW_PID" 2>/dev/null
restore
result rolled_back "Yeni sürüm açılış kontrolünü geçemedi; önceki sürüm ve veritabanı geri yüklendi."
"$LAUNCH" &
exit 1
'''

WINDOWS_SCRIPT = r'''param([string]$Job)
# Kelebek artımlı güncelleyici (Windows). Uygulama kapandıktan sonra çalışır.
$ErrorActionPreference = "Stop"
$j = Get-Content -Raw -Encoding UTF8 $Job | ConvertFrom-Json
Start-Transcript -Append -Path $j.log_file | Out-Null
function Write-Result($status, $message) {
  @{ status = $status; from_version = $j.from_version; to_version = $j.to_version; finished_at = (Get-Date).ToUniversalTime().ToString("o"); message = $message; safety_backup = $j.safety_backup } | ConvertTo-Json | Set-Content -Encoding UTF8 $j.result_file
}
try { Wait-Process -Id $j.app_pid -Timeout 120 -ErrorAction SilentlyContinue } catch {}
if (Get-Process -Id $j.app_pid -ErrorAction SilentlyContinue) { Write-Result "failed" "Uygulama kapanmadı; güncelleme uygulanmadı."; exit 1 }
Start-Sleep -Milliseconds 800
$root = $j.app_root; $rb = $j.rollback; $staged = $j.staged
if (Test-Path $rb) { Remove-Item -Recurse -Force $rb }
New-Item -ItemType Directory -Force -Path (Join-Path $rb "files") | Out-Null
$newFiles = @()
$changed = @(Get-Content -Encoding UTF8 (Join-Path $staged "files.txt") | Where-Object { $_ })
$removed = @(Get-Content -Encoding UTF8 (Join-Path $staged "removed.txt") | Where-Object { $_ })
foreach ($rel in ($changed + $removed)) {
  $src = Join-Path $root $rel
  if (Test-Path -LiteralPath $src) { $dst = Join-Path (Join-Path $rb "files") $rel; New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null; Copy-Item -LiteralPath $src $dst -Force }
  else { $newFiles += $rel }
}
foreach ($suffix in @("", "-wal", "-shm")) { if (Test-Path -LiteralPath ($j.db_path + $suffix)) { Copy-Item -LiteralPath ($j.db_path + $suffix) (Join-Path $rb ("db" + $suffix)) -Force } }
function Restore-Previous {
  foreach ($rel in $newFiles) { Remove-Item -LiteralPath (Join-Path $root $rel) -Force -ErrorAction SilentlyContinue }
  $base = Join-Path $rb "files"
  Get-ChildItem -Recurse -File $base | ForEach-Object { $rel = $_.FullName.Substring($base.Length + 1); $dst = Join-Path $root $rel; New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null; Copy-Item -LiteralPath $_.FullName $dst -Force }
  foreach ($suffix in @("", "-wal", "-shm")) { Remove-Item -LiteralPath ($j.db_path + $suffix) -Force -ErrorAction SilentlyContinue; $saved = Join-Path $rb ("db" + $suffix); if (Test-Path -LiteralPath $saved) { Copy-Item -LiteralPath $saved ($j.db_path + $suffix) -Force } }
}
try {
  foreach ($rel in $changed) { $dst = Join-Path $root $rel; New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null; Copy-Item -LiteralPath (Join-Path (Join-Path $staged "files") $rel) $dst -Force }
  foreach ($rel in $removed) { Remove-Item -LiteralPath (Join-Path $root $rel) -Force -ErrorAction SilentlyContinue }
} catch {
  Restore-Previous; Write-Result "rolled_back" "Dosyalar kopyalanamadı; önceki sürüm geri yüklendi."; Start-Process $j.launch[0]; exit 1
}
Remove-Item -LiteralPath $j.verify_file -Force -ErrorAction SilentlyContinue
$env:KELEBEK_UPDATE_VERIFY = $j.verify_file
$proc = Start-Process -FilePath $j.launch[0] -PassThru
$deadline = (Get-Date).AddSeconds([int]$j.timeout)
while ((Get-Date) -lt $deadline -and -not (Test-Path -LiteralPath $j.verify_file) -and -not $proc.HasExited) { Start-Sleep -Milliseconds 500 }
if (Test-Path -LiteralPath $j.verify_file) { Write-Result "success" "Güncelleme tamamlandı."; Remove-Item -Recurse -Force (Join-Path $staged "files") -ErrorAction SilentlyContinue; exit 0 }
if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue; Start-Sleep -Seconds 1 }
Remove-Item Env:KELEBEK_UPDATE_VERIFY
Restore-Previous
Write-Result "rolled_back" "Yeni sürüm açılış kontrolünü geçemedi; önceki sürüm ve veritabanı geri yüklendi."
Start-Process $j.launch[0]
exit 1
'''
