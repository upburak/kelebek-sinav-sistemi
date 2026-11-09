"""Portable backup creation endpoints."""

import logging
import sqlite3
import zipfile
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request, send_file

from kelebek.config import get_data_dir
from kelebek.services.backup_restore import (
    apply_confirmed_restore,
    discard_pending_restore,
    inspect_uploaded_backup,
)
from kelebek.services.backup import BACKUP_RETENTION_COUNT, build_backup_package


backups_api = Blueprint("backups", __name__)
logger = logging.getLogger(__name__)


@backups_api.get("/backups/status")
def get_backup_status():
    """Return safe metadata about automatic backups without listing user files."""
    backup_dir = get_data_dir() / "backups"
    daily_files = sorted(
        (path for path in backup_dir.glob("automatic-daily-*.zip")
         if path.is_file() and not path.is_symlink()),
        key=lambda path: path.name,
        reverse=True,
    )
    today = datetime.now().astimezone().date().isoformat()
    today_file = backup_dir / f"automatic-daily-{today}.zip"
    latest = daily_files[0] if daily_files else None
    return jsonify({
        "daily_backup_today": (
            today_file.is_file() and not today_file.is_symlink() and today_file.stat().st_size > 0
        ),
        "latest_daily_backup_at": datetime.fromtimestamp(
            latest.stat().st_mtime
        ).isoformat() if latest else None,
        "stored_daily_backups": len(daily_files),
        "retention_limit": BACKUP_RETENTION_COUNT,
    })


@backups_api.post("/backups")
def download_backup():
    """Create a consistent ZIP snapshot and stream it to the local user."""
    try:
        stream, file_name, manifest = build_backup_package()
    except (OSError, ValueError) as error:
        logger.exception("Yedek paketi oluşturulamadı.")
        return jsonify({"error": str(error)}), 500
    except Exception:
        logger.exception("Yedek paketi oluşturulamadı.")
        return jsonify({"error": "Yedek paketi oluşturulamadı. Günlükleri inceleyin."}), 500

    response = send_file(
        stream,
        mimetype="application/zip",
        as_attachment=True,
        download_name=file_name,
        max_age=0,
    )
    response.call_on_close(stream.close)
    response.headers["X-Backup-Format"] = "kelebek-portable-backup-v1"
    response.headers["X-Backup-Created-At"] = manifest["created_at"]
    response.headers["X-Backup-File-Count"] = str(len(manifest["files"]))
    response.headers["X-Backup-Schema-Revision"] = manifest["schema_revision"] or "bilinmiyor"
    return response


@backups_api.post("/backups/restore/inspect")
def inspect_backup():
    """Validate an uploaded portable package and return a metadata-only preview."""
    uploaded = request.files.get("backup")
    if uploaded is None or not uploaded.filename:
        return jsonify({"error": "Önizleme için bir ZIP yedek dosyası seçin."}), 400
    try:
        token, preview = inspect_uploaded_backup(uploaded.stream)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except (OSError, sqlite3.DatabaseError, zipfile.BadZipFile):
        logger.exception("Yedek paketi doğrulanamadı.")
        return jsonify({"error": "Yedek paketi açılamadı veya doğrulanamadı."}), 400
    except Exception:
        logger.exception("Yedek paketi doğrulanamadı.")
        return jsonify({"error": "Yedek paketi doğrulanırken beklenmeyen bir hata oluştu."}), 500
    return jsonify({"token": token, "preview": preview})


@backups_api.post("/backups/restore/cancel")
def cancel_restore_preview():
    """Discard an unconfirmed preview and remove its staged copy."""
    payload = request.get_json(silent=True)
    token = payload.get("token") if isinstance(payload, dict) else None
    if not isinstance(token, str) or len(token) > 128:
        return jsonify({"cancelled": False}), 400
    return jsonify({"cancelled": discard_pending_restore(token)})


@backups_api.post("/backups/restore/confirm")
def confirm_restore():
    """Restore only a staged package after the app's explicit final confirmation."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Geri yükleme onay bilgisi geçersiz."}), 400
    token = payload.get("token")
    if not isinstance(token, str) or len(token) > 128:
        return jsonify({"error": "Yedek önizlemesi bulunamadı. Dosyayı yeniden seçin."}), 400
    try:
        result = apply_confirmed_restore(
            token,
            payload.get("confirmed") is True,
            current_app.extensions["kelebek_engine"],
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Exception:
        logger.exception("Onaylanan yedek geri yüklenemedi.")
        return jsonify({
            "error": "Geri yükleme tamamlanamadı. Mevcut veriler korundu; günlükleri inceleyin."
        }), 500
    return jsonify(result)
