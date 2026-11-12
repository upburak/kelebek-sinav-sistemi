"""Kelebek Sınav Sistemi Flask uygulaması."""

import re
import threading
from pathlib import Path

from flask import Flask, g, jsonify, request, send_from_directory

from kelebek.api.academic_years import academic_year_api
from kelebek.api.backups import backups_api
from kelebek.api.bulk_delete import bulk_delete_api
from kelebek.api.classrooms import classrooms_api
from kelebek.api.exam_lifecycle import exam_lifecycle_api, guard_exam_writes
from kelebek.api.exam_organizations import exam_organizations_api
from kelebek.api.exam_periods import exam_periods_api
from kelebek.api.health import health_api
from kelebek.api.school_profile import school_profile_api
from kelebek.api.student_import import student_import_api
from kelebek.api.students import students_api
from kelebek.api.updates import updates_api
from kelebek.config import configure_logging
from kelebek.db import initialize_database
from kelebek.services.backup import ensure_daily_backup
from kelebek.services.backup_restore import (
    cleanup_stale_restore_staging,
    recover_interrupted_restore,
)

_api_request_lock = threading.RLock()
# Uzun dağıtım sürerken ilerleme, durdurma ve sekme kilidi istekleri beklememeli.
_LOCK_FREE_PATH = re.compile(r"/distribution-progress(/stop)?$|^/api/edit-locks|^/api/health$")


def _register_frontend(app: Flask, frontend_dist: Path) -> None:
    """Paketlenmiş uygulamada derlenmiş arayüzü aynı yerel adresten sun."""
    # Kök, kurulum yolu sembolik bağ içerse de (macOS'ta /var, bağlı Applications
    # klasörleri) karşılaştırmanın doğru çalışması için bir kez çözümlenir.
    root = frontend_dist.resolve()
    index_name = (root / "index.html").name

    @app.get("/", defaults={"path": ""})
    @app.get("/<path:path>")
    def frontend(path: str):
        if path.startswith("api/"):
            return jsonify({"error": "Bulunamadı."}), 404
        if path:
            try:
                target = (root / path).resolve()
            except OSError:
                target = None
            if target is not None and target.is_file() and target != root and target.is_relative_to(root):
                return send_from_directory(root, target.relative_to(root).as_posix())
        return send_from_directory(root, index_name)


def create_app(frontend_dist: Path | None = None, allowed_hosts: set[str] | None = None) -> Flask:
    """Uygulamayı oluştur, veritabanını güncelle ve API uç noktalarını kaydet."""
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 513 * 1024 * 1024
    configure_logging(app.logger)
    if recover_interrupted_restore():
        app.logger.warning("Kesintiye uğrayan geri yükleme eski verilerden geri alındı.")
    cleanup_stale_restore_staging()
    initialize_database(app)
    try:
        ensure_daily_backup()
    except Exception:
        app.logger.exception("Günlük otomatik yedek alınamadı; uygulama açılmaya devam ediyor.")

    if allowed_hosts:
        @app.before_request
        def reject_foreign_hosts():
            if request.host not in allowed_hosts:
                return jsonify({"error": "Yalnızca bu bilgisayardan erişilebilir."}), 403
            origin = request.headers.get("Origin")
            if origin and origin.split("://", 1)[-1] not in allowed_hosts:
                return jsonify({"error": "Yalnızca bu bilgisayardan erişilebilir."}), 403

    @app.before_request
    def ensure_daily_backup_for_active_day():
        if request.path.startswith("/api/") and not _LOCK_FREE_PATH.search(request.path):
            _api_request_lock.acquire()
            g._kelebek_api_lock_acquired = True
            try:
                ensure_daily_backup()
            except Exception:
                app.logger.exception("Günlük otomatik yedek alınamadı.")

    @app.teardown_request
    def release_api_request_lock(_error=None):
        if getattr(g, "_kelebek_api_lock_acquired", False):
            g._kelebek_api_lock_acquired = False
            _api_request_lock.release()

    app.register_blueprint(health_api, url_prefix="/api")
    app.register_blueprint(school_profile_api, url_prefix="/api")
    app.register_blueprint(academic_year_api, url_prefix="/api")
    app.register_blueprint(backups_api, url_prefix="/api")
    app.register_blueprint(classrooms_api, url_prefix="/api")
    app.register_blueprint(student_import_api, url_prefix="/api")
    app.register_blueprint(students_api, url_prefix="/api")
    app.register_blueprint(exam_organizations_api, url_prefix="/api")
    app.register_blueprint(exam_periods_api, url_prefix="/api")
    app.register_blueprint(bulk_delete_api, url_prefix="/api")
    app.register_blueprint(exam_lifecycle_api, url_prefix="/api")
    app.register_blueprint(updates_api, url_prefix="/api")
    app.before_request(guard_exam_writes)
    if frontend_dist and (frontend_dist / "index.html").is_file():
        _register_frontend(app, frontend_dist)

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify({"error": "İstek boyutu 513 MB sınırını aşıyor."}), 413

    return app
