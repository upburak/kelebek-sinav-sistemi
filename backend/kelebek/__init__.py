"""Kelebek Sınav Sistemi Flask uygulaması."""

from flask import Flask

from kelebek.api.health import health_api
from kelebek.config import configure_logging


def create_app() -> Flask:
    """Uygulamayı oluştur ve API uç noktalarını kaydet."""
    app = Flask(__name__)
    configure_logging(app.logger)
    app.register_blueprint(health_api, url_prefix="/api")
    return app
