"""Portable backup creation endpoints."""

import logging

from flask import Blueprint, jsonify, send_file

from kelebek.services.backup import build_backup_package


backups_api = Blueprint("backups", __name__)
logger = logging.getLogger(__name__)


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
