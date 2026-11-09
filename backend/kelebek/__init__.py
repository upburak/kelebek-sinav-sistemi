"""Kelebek Sınav Sistemi Flask uygulaması."""

import threading

from flask import Flask, g, jsonify, request

from kelebek.api.academic_years import academic_year_api
from kelebek.api.backups import backups_api
from kelebek.api.classrooms import classrooms_api
from kelebek.api.exam_organizations import exam_organizations_api
from kelebek.api.health import health_api
from kelebek.api.school_profile import school_profile_api
from kelebek.api.student_import import student_import_api
from kelebek.api.students import students_api
from kelebek.config import configure_logging
from kelebek.db import initialize_database
from kelebek.services.backup import ensure_daily_backup
from kelebek.services.backup_restore import (
    cleanup_stale_restore_staging,
    recover_interrupted_restore,
)


_api_request_lock = threading.RLock()


def create_app() -> Flask:
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

    @app.before_request
    def ensure_daily_backup_for_active_day():
        if request.path.startswith("/api/"):
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

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify({"error": "İstek boyutu 513 MB sınırını aşıyor."}), 413

    return app
