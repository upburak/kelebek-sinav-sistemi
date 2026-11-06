"""Kelebek Sınav Sistemi Flask uygulaması."""

from flask import Flask, jsonify

from kelebek.api.academic_years import academic_year_api
from kelebek.api.classrooms import classrooms_api
from kelebek.api.health import health_api
from kelebek.api.student_import import student_import_api
from kelebek.config import configure_logging
from kelebek.db import initialize_database


def create_app() -> Flask:
    """Uygulamayı oluştur, veritabanını güncelle ve API uç noktalarını kaydet."""
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024
    configure_logging(app.logger)
    initialize_database(app)
    app.register_blueprint(health_api, url_prefix="/api")
    app.register_blueprint(academic_year_api, url_prefix="/api")
    app.register_blueprint(classrooms_api, url_prefix="/api")
    app.register_blueprint(student_import_api, url_prefix="/api")

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify({"error": "Dosya boyutu 12 MB sınırını aşıyor."}), 413

    return app
