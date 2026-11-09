"""Validation and guarded restore of portable Kelebek backup packages."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import shutil
import sqlite3
import threading
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from secrets import token_urlsafe

from alembic import command
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import URL, create_engine

from kelebek.config import get_data_dir, get_database_path
from kelebek.db import _migration_config
from kelebek.services.backup import (
    BACKUP_FORMAT,
    BACKUP_FORMAT_VERSION,
    BACKUP_RETENTION_COUNT,
    _app_version,
    _prune_backups,
    _store_package,
)


MAX_BACKUP_BYTES = 512 * 1024 * 1024
MAX_BACKUP_FILES = 4096
MAX_MANIFEST_BYTES = 1024 * 1024
PENDING_RESTORE_TTL_SECONDS = 15 * 60
_pending_lock = threading.Lock()


@dataclass
class PendingRestore:
    token: str
    stage_dir: Path
    database_path: Path
    reports_path: Path
    preview: dict
    created_at: float


_pending_restores: dict[str, PendingRestore] = {}


def _read_only_sqlite_uri(path: Path) -> str:
    return f"{path.resolve().as_uri()}?mode=ro"


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)


def cleanup_stale_restore_staging(data_dir: Path | None = None) -> int:
    """Remove obsolete restore staging entries without traversing symlinks."""
    staging_root = (data_dir or get_data_dir()) / ".restore-staging"
    if staging_root.is_symlink() or not staging_root.is_dir():
        return 0

    return _clean_staging_tree(staging_root)


def _clean_staging_tree(directory: Path) -> int:
    removed = 0
    if directory.is_symlink() or not directory.is_dir():
        return 0
    try:
        with os.scandir(directory) as entries:
            for entry in entries:
                child = Path(entry.path)
                try:
                    if entry.is_symlink():
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        removed += _clean_staging_tree(child)
                        try:
                            child.rmdir()
                            removed += 1
                        except OSError:
                            continue
                    elif entry.is_file(follow_symlinks=False):
                        child.unlink()
                        removed += 1
                except OSError:
                    # Leave entries that cannot be safely inspected or removed.
                    continue
    except OSError:
        return removed
    return removed


def _write_restore_journal(data_dir: Path, journal: dict) -> None:
    journal_path = data_dir / ".restore-transaction.json"
    temporary_path = data_dir / ".restore-transaction.tmp"
    with temporary_path.open("w", encoding="utf-8") as destination:
        os.chmod(temporary_path, 0o600)
        json.dump(journal, destination, ensure_ascii=False, sort_keys=True)
        destination.flush()
        os.fsync(destination.fileno())
    os.replace(temporary_path, journal_path)
    try:
        descriptor = os.open(data_dir, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError:
        pass


def recover_interrupted_restore(data_dir: Path | None = None) -> bool:
    """Finish cleanup or roll back a restore interrupted between atomic swaps."""
    data_dir = data_dir or get_data_dir()
    journal_path = data_dir / ".restore-transaction.json"
    if not journal_path.is_file():
        return False
    try:
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError("Geri yükleme işlem günlüğü okunamadı; veritabanı açılmadı.") from error
    transaction_id = journal.get("transaction_id") if isinstance(journal, dict) else None
    if (
        not isinstance(transaction_id, str)
        or not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", transaction_id)
        or journal.get("state") not in {"prepared", "committed"}
        or not isinstance(journal.get("reports_existed"), bool)
    ):
        raise RuntimeError("Geri yükleme işlem günlüğü geçersiz; veritabanı açılmadı.")

    database_path = data_dir / "kelebek.sqlite3"
    reports_path = data_dir / "Exports" / "PDF"
    stage_dir = data_dir / ".restore-staging" / transaction_id
    old_database = data_dir / f".restore-old-database-{transaction_id}.sqlite3"
    old_reports = reports_path.with_name(f".restore-old-pdf-{transaction_id}")
    try:
        if journal["state"] == "prepared":
            if old_database.exists() or old_database.is_symlink():
                _remove_path(database_path)
                os.replace(old_database, database_path)
            if old_reports.exists() or old_reports.is_symlink():
                _remove_path(reports_path)
                os.replace(old_reports, reports_path)
            elif not journal["reports_existed"] and not (stage_dir / "reports").exists():
                _remove_path(reports_path)

        _remove_path(old_database)
        _remove_path(old_reports)
        if stage_dir.is_dir() and not stage_dir.is_symlink():
            _clean_staging_tree(stage_dir)
            try:
                stage_dir.rmdir()
            except OSError:
                pass
        journal_path.unlink(missing_ok=True)
        return True
    except OSError as error:
        raise RuntimeError(
            "Kesilen geri yükleme otomatik olarak geri alınamadı; işlem günlüğü korundu."
        ) from error


def _safe_member_path(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if (
        not name or "\\" in name or path.is_absolute()
        or not path.parts or any(part in ("", ".", "..") for part in path.parts)
        or ":" in path.parts[0]
    ):
        raise ValueError("Yedek paketinde güvenli olmayan dosya yolu var.")
    return path


def _upgrade_and_check_database(database_path: Path, schema_revision: str) -> tuple[str, str]:
    engine = create_engine(URL.create("sqlite", database=str(database_path)))
    try:
        config = _migration_config(engine)
        script = ScriptDirectory.from_config(config)
        head_revision = script.get_current_head()
        if not head_revision:
            raise ValueError("Uygulamanın veritabanı şema sürümü bulunamadı.")
        try:
            script.get_revision(schema_revision)
            path = list(script.iterate_revisions(head_revision, schema_revision))
        except Exception as error:
            raise ValueError("Yedek veritabanı şema sürümü bu uygulamayla uyumlu değil.") from error
        compatible = (
            schema_revision == head_revision
            or bool(path and path[-1].down_revision == schema_revision)
        )
        if not compatible:
            raise ValueError("Yedek şeması bu uygulamayla güvenli biçimde güncellenemiyor.")

        with engine.connect() as connection:
            current_revision = MigrationContext.configure(connection).get_current_revision()
            if current_revision != schema_revision:
                raise ValueError("Manifest şema sürümü veritabanıyla eşleşmiyor.")
            connection.commit()
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            connection.commit()

        with sqlite3.connect(_read_only_sqlite_uri(database_path), uri=True) as database:
            integrity = database.execute("PRAGMA integrity_check").fetchone()
            foreign_key_error = database.execute("PRAGMA foreign_key_check").fetchone()
            revision_row = database.execute(
                "SELECT version_num FROM alembic_version LIMIT 1"
            ).fetchone()
        if not integrity or integrity[0] != "ok":
            raise ValueError("Yedek veritabanı bütünlük kontrolünden geçemedi.")
        if foreign_key_error:
            raise ValueError("Yedek veritabanında bağlantısı kopuk kayıtlar var.")
        if not revision_row or revision_row[0] != head_revision:
            raise ValueError("Yedek veritabanı güncel şema sürümüne taşınamadı.")
        return schema_revision, head_revision
    finally:
        engine.dispose()


def _validate_and_stage(archive_path: Path, stage_dir: Path) -> dict:
    stage_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    database_path = stage_dir / "kelebek.sqlite3"
    reports_path = stage_dir / "reports"
    reports_path.mkdir(mode=0o700)
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            entries = archive.infolist()
            if len(entries) < 2 or len(entries) > MAX_BACKUP_FILES:
                raise ValueError("Yedek paketindeki dosya sayısı geçersiz.")
            names: set[str] = set()
            total_size = 0
            manifest_info = None
            for info in entries:
                if info.is_dir() or info.filename in names:
                    raise ValueError("Yedek paketinde yinelenen veya beklenmeyen dosya var.")
                names.add(info.filename)
                path = _safe_member_path(info.filename)
                mode = (info.external_attr >> 16) & 0xFFFF
                if mode and (mode & 0o170000) == 0o120000:
                    raise ValueError("Yedek paketinde sembolik bağlantı kullanılamaz.")
                if info.flag_bits & 0x1:
                    raise ValueError("Şifreli ZIP paketleri bu sürümde desteklenmiyor.")
                if info.file_size > MAX_BACKUP_BYTES:
                    raise ValueError("Yedek dosyası izin verilen boyutu aşıyor.")
                total_size += info.file_size
                if total_size > MAX_BACKUP_BYTES:
                    raise ValueError(
                        "Yedek paketinin açılmış toplam boyutu izin verilen sınırı aşıyor."
                    )
                if path.as_posix() == "manifest.json":
                    manifest_info = info

            if manifest_info is None or manifest_info.file_size > MAX_MANIFEST_BYTES:
                raise ValueError("Yedek paketi manifest dosyası eksik veya fazla büyük.")
            try:
                manifest = json.loads(archive.read(manifest_info))
            except (UnicodeDecodeError, json.JSONDecodeError, zipfile.BadZipFile) as error:
                raise ValueError("Yedek paketi manifest dosyası okunamadı.") from error
            if not isinstance(manifest, dict) or manifest.get("format") != BACKUP_FORMAT:
                raise ValueError("Bu dosya Kelebek taşınabilir yedek paketi değil.")
            if (
                type(manifest.get("format_version")) is not int
                or manifest["format_version"] != BACKUP_FORMAT_VERSION
            ):
                raise ValueError("Yedek paket biçimi bu uygulamayla uyumlu değil.")
            schema_revision = manifest.get("schema_revision")
            files = manifest.get("files")
            if (
                not isinstance(schema_revision, str) or len(schema_revision) > 128
                or not isinstance(files, list) or not files
            ):
                raise ValueError("Yedek paketi manifest bilgileri eksik.")

            declared: set[str] = {"manifest.json"}
            database_seen = False
            report_count = 0
            for item in files:
                if not isinstance(item, dict):
                    raise ValueError("Yedek dosya listesi geçersiz.")
                name = item.get("path")
                size = item.get("size_bytes")
                expected_hash = item.get("sha256")
                if not isinstance(name, str) or name in declared:
                    raise ValueError("Yedek dosya listesinde yinelenen veya geçersiz yol var.")
                path = _safe_member_path(name)
                if name == "database/kelebek.sqlite3":
                    target = database_path
                    database_seen = True
                elif (
                    path.parts[:3] == ("files", "Exports", "PDF")
                    and len(path.parts) == 4 and path.suffix.casefold() == ".pdf"
                ):
                    target = reports_path / path.name
                    report_count += 1
                else:
                    raise ValueError("Yedek paketi beklenmeyen bir dosya içeriyor.")
                if type(size) is not int or size < 0 or not isinstance(expected_hash, str):
                    raise ValueError("Yedek dosya boyutu veya SHA-256 özeti geçersiz.")
                if len(expected_hash) != 64 or any(
                    char not in "0123456789abcdef" for char in expected_hash.lower()
                ):
                    raise ValueError("Yedek dosyasının SHA-256 özeti geçersiz.")
                if name not in names:
                    raise ValueError("Manifestte listelenen dosya ZIP paketinde bulunamadı.")
                info = archive.getinfo(name)
                if info.file_size != size:
                    raise ValueError("Yedek dosya boyutu manifest ile eşleşmiyor.")
                declared.add(name)
                digest = hashlib.sha256()
                with archive.open(info, "r") as source, target.open("xb") as destination:
                    os.chmod(target, 0o600)
                    while True:
                        chunk = source.read(1024 * 1024)
                        if not chunk:
                            break
                        digest.update(chunk)
                        destination.write(chunk)
                if not hmac.compare_digest(digest.hexdigest(), expected_hash.lower()):
                    raise ValueError("Yedek dosyasının SHA-256 doğrulaması başarısız oldu.")

            if not database_seen or declared != names:
                raise ValueError("Yedek paketi manifest ve dosya listesi eşleşmiyor.")

        original_revision, target_revision = _upgrade_and_check_database(
            database_path, schema_revision
        )
        created_at = manifest.get("created_at")
        try:
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except (AttributeError, ValueError) as error:
            raise ValueError("Yedek oluşturulma zamanı geçersiz.") from error
        app_version = manifest.get("application_version")
        if not isinstance(app_version, str):
            raise ValueError("Yedek uygulama sürümü bilgisi eksik.")
        app_version_match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", app_version)
        current_version_match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", _app_version())
        if not app_version_match or not current_version_match:
            raise ValueError("Uygulama sürüm bilgisi doğrulanamadı.")
        backup_version = tuple(map(int, app_version_match.groups()))
        current_version = tuple(map(int, current_version_match.groups()))
        if backup_version > current_version:
            raise ValueError("Yedek daha yeni bir uygulama sürümünde oluşturulmuş.")
        return {
            "created_at": created_at.astimezone(timezone.utc).isoformat(),
            "application_version": app_version,
            "schema_revision": original_revision,
            "target_schema_revision": target_revision,
            "migration_required": original_revision != target_revision,
            "file_count": len(files),
            "report_count": report_count,
            "database_integrity": "ok",
            "sha256_verified": True,
        }
    except Exception:
        shutil.rmtree(stage_dir, ignore_errors=True)
        raise


def inspect_uploaded_backup(upload_stream) -> tuple[str, dict]:
    """Validate an uploaded package and retain a private staged copy for confirmation."""
    data_dir = get_data_dir()
    staging_root = data_dir / ".restore-staging"
    staging_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(staging_root, 0o700)
    token = token_urlsafe(32)
    stage_dir = staging_root / token
    upload_path = stage_dir.with_suffix(".upload")
    try:
        with upload_path.open("xb") as destination:
            os.chmod(upload_path, 0o600)
            size = 0
            while True:
                chunk = upload_stream.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_BACKUP_BYTES:
                    raise ValueError("Yedek paketi 512 MB sınırını aşıyor.")
                destination.write(chunk)
        preview = _validate_and_stage(upload_path, stage_dir)
        upload_path.unlink(missing_ok=True)
        pending = PendingRestore(
            token=token,
            stage_dir=stage_dir,
            database_path=stage_dir / "kelebek.sqlite3",
            reports_path=stage_dir / "reports",
            preview=preview,
            created_at=time.monotonic(),
        )
        with _pending_lock:
            expired = [key for key, value in _pending_restores.items()
                       if time.monotonic() - value.created_at > PENDING_RESTORE_TTL_SECONDS]
            for key in expired:
                stale = _pending_restores.pop(key)
                shutil.rmtree(stale.stage_dir, ignore_errors=True)
            _pending_restores[token] = pending
        expiry = threading.Timer(
            PENDING_RESTORE_TTL_SECONDS,
            discard_pending_restore,
            args=(token,),
        )
        expiry.daemon = True
        expiry.start()
        return token, preview
    except Exception:
        upload_path.unlink(missing_ok=True)
        shutil.rmtree(stage_dir, ignore_errors=True)
        raise


def discard_pending_restore(token: str) -> bool:
    """Remove an unconfirmed staged package and its private temporary data."""
    with _pending_lock:
        pending = _pending_restores.pop(token, None)
    if pending is None:
        return False
    shutil.rmtree(pending.stage_dir, ignore_errors=True)
    return True


def _integrity_check(path: Path) -> None:
    with sqlite3.connect(_read_only_sqlite_uri(path), uri=True) as database:
        result = database.execute("PRAGMA integrity_check").fetchone()
        foreign_key_error = database.execute("PRAGMA foreign_key_check").fetchone()
    if not result or result[0] != "ok" or foreign_key_error:
        raise RuntimeError("Geri yüklenen veritabanının bütünlük kontrolü başarısız oldu.")


def apply_confirmed_restore(token: str, confirmed: bool, engine) -> dict:
    """Restore a staged backup after explicit confirmation, rolling back on failure."""
    if confirmed is not True:
        raise ValueError("Geri yükleme için uygulama içindeki açık son onay gereklidir.")
    with _pending_lock:
        pending = _pending_restores.get(token)
        if pending is None:
            raise ValueError("Önizleme süresi dolmuş. Yedek dosyasını yeniden seçin.")
        if time.monotonic() - pending.created_at > PENDING_RESTORE_TTL_SECONDS:
            _pending_restores.pop(token, None)
            shutil.rmtree(pending.stage_dir, ignore_errors=True)
            raise ValueError("Önizleme süresi dolmuş. Yedek dosyasını yeniden seçin.")
        _pending_restores.pop(token, None)

    data_dir = get_data_dir()
    database_path = get_database_path()
    pdf_dir = data_dir / "Exports" / "PDF"
    restore_backup_dir = data_dir / "backups"
    restore_backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    safety_path = restore_backup_dir / f"safety-restore-{stamp}.zip"
    transaction_id = pending.token
    journal = {
        "transaction_id": transaction_id,
        "state": "prepared",
        "reports_existed": pdf_dir.exists() or pdf_dir.is_symlink(),
    }
    journal_written = False
    try:
        _store_package(safety_path)
        safety_stage = data_dir / ".restore-staging" / f"verify-{stamp}"
        _validate_and_stage(safety_path, safety_stage)
        shutil.rmtree(safety_stage, ignore_errors=True)
        _prune_backups("safety-restore-*.zip", BACKUP_RETENTION_COUNT)

        _write_restore_journal(data_dir, journal)
        journal_written = True
        engine.dispose()
        if not database_path.is_file():
            raise RuntimeError("Mevcut veritabanı bulunamadı; geri yükleme durduruldu.")
        old_database = data_dir / f".restore-old-database-{transaction_id}.sqlite3"
        old_reports = pdf_dir.with_name(f".restore-old-pdf-{transaction_id}")
        os.replace(database_path, old_database)
        os.replace(pending.database_path, database_path)

        pdf_dir.parent.mkdir(parents=True, exist_ok=True)
        if pdf_dir.exists() or pdf_dir.is_symlink():
            os.replace(pdf_dir, old_reports)
        os.replace(pending.reports_path, pdf_dir)
        _integrity_check(database_path)
        _write_restore_journal(data_dir, {**journal, "state": "committed"})
    except Exception:
        engine.dispose()
        if journal_written:
            recover_interrupted_restore(data_dir)
        engine.dispose()
        raise
    else:
        recover_interrupted_restore(data_dir)
        engine.dispose()
        return {"restored": True, "safety_backup": safety_path.name, **pending.preview}
    finally:
        shutil.rmtree(pending.stage_dir, ignore_errors=True)
