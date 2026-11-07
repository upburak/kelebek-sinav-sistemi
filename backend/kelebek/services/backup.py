"""Portable, integrity-checked backups for local school data."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import logging
import os
import shutil
import sqlite3
import tempfile
import threading
import zipfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from tempfile import SpooledTemporaryFile
from typing import BinaryIO

from kelebek.config import get_data_dir, get_database_path


BACKUP_FORMAT = "kelebek-portable-backup"
BACKUP_FORMAT_VERSION = 1
SPOOL_MEMORY_LIMIT = 8 * 1024 * 1024
BACKUP_RETENTION_COUNT = 30
_backup_lock = threading.Lock()
logger = logging.getLogger(__name__)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _app_version() -> str:
    try:
        return importlib.metadata.version("kelebek-sinav-sistemi")
    except importlib.metadata.PackageNotFoundError:
        return "0.1.0"


def build_backup_package() -> tuple[BinaryIO, str, dict]:
    """Build a portable ZIP from a consistent SQLite snapshot and stored reports."""
    data_dir = get_data_dir()
    database_path = get_database_path()
    if not database_path.is_file():
        raise FileNotFoundError("Uygulama veritabanı bulunamadı.")

    created_at = datetime.now(timezone.utc)
    stamp = created_at.strftime("%Y%m%d-%H%M%S-%f-UTC")
    stream = SpooledTemporaryFile(max_size=SPOOL_MEMORY_LIMIT, mode="w+b")

    try:
        with tempfile.TemporaryDirectory(prefix="kelebek-backup-") as temporary_dir:
            snapshot_path = Path(temporary_dir) / "kelebek.sqlite3"
            with closing(sqlite3.connect(database_path)) as source, closing(
                sqlite3.connect(snapshot_path)
            ) as destination:
                source.backup(destination)
                result = destination.execute("PRAGMA integrity_check").fetchone()
                if not result or result[0] != "ok":
                    raise ValueError("Veritabanı bütünlük denetimi başarısız oldu.")
                version_row = destination.execute(
                    "SELECT version_num FROM alembic_version LIMIT 1"
                ).fetchone()
            files = [(snapshot_path, "database/kelebek.sqlite3")]
            reports_dir = data_dir / "Exports" / "PDF"
            if reports_dir.is_dir():
                for report_path in sorted(reports_dir.glob("*.pdf")):
                    if report_path.is_file() and not report_path.is_symlink():
                        relative = report_path.relative_to(data_dir).as_posix()
                        report_snapshot = Path(temporary_dir) / "reports" / relative
                        report_snapshot.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(report_path, report_snapshot)
                        files.append((report_snapshot, f"files/{relative}"))

            manifest = {
                "format": BACKUP_FORMAT,
                "format_version": BACKUP_FORMAT_VERSION,
                "application_version": _app_version(),
                "schema_revision": version_row[0] if version_row else None,
                "created_at": created_at.isoformat(),
                "files": [
                    {
                        "path": archive_path,
                        "size_bytes": path.stat().st_size,
                        "sha256": _sha256(path),
                    }
                    for path, archive_path in files
                ],
            }
            manifest_bytes = json.dumps(
                manifest, ensure_ascii=False, sort_keys=True, indent=2
            ).encode("utf-8")
            with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for path, archive_path in files:
                    archive.write(path, archive_path)
                archive.writestr("manifest.json", manifest_bytes)

        stream.seek(0)
        return stream, f"kelebek-yedek-{stamp}.zip", manifest
    except Exception:
        stream.close()
        raise


def _store_package(target: Path) -> None:
    """Write a complete backup atomically so interrupted writes are ignored."""
    stream, _download_name, _manifest = build_backup_package()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=".kelebek-backup-", suffix=".tmp",
            dir=target.parent, delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            shutil.copyfileobj(stream, temporary)
            temporary.flush()
            os.fsync(temporary.fileno())
        try:
            os.chmod(temporary_path, 0o600)
        except OSError:
            logger.warning("Yedek dosyası erişim izinleri ayarlanamadı.")
        os.replace(temporary_path, target)
    finally:
        stream.close()
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


def _prune_backups(pattern: str, keep: int) -> None:
    backup_dir = get_data_dir() / "backups"
    candidates = sorted(
        (path for path in backup_dir.glob(pattern) if path.is_file() and not path.is_symlink()),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
        reverse=True,
    )
    for old_path in candidates[keep:]:
        try:
            old_path.unlink()
        except OSError:
            logger.warning("Eski otomatik yedek temizlenemedi: %s", old_path.name)


def ensure_daily_backup(now: datetime | None = None) -> Path | None:
    """Create one automatic package per local calendar day; keep the latest 30."""
    now = now or datetime.now().astimezone()
    target = get_data_dir() / "backups" / f"automatic-daily-{now.date().isoformat()}.zip"
    with _backup_lock:
        if target.is_file():
            return None
        _store_package(target)
        _prune_backups("automatic-daily-*.zip", BACKUP_RETENTION_COUNT)
        return target


def create_safety_backup(reason: str) -> Path:
    """Create a named pre-operation package for a supported critical action."""
    if reason != "student-import":
        raise ValueError("Güvenlik yedeği nedeni desteklenmiyor.")
    backup_dir = get_data_dir() / "backups"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f-UTC")
    target = backup_dir / f"safety-{reason}-{stamp}.zip"
    with _backup_lock:
        _store_package(target)
        _prune_backups(f"safety-{reason}-*.zip", BACKUP_RETENTION_COUNT)
    return target
