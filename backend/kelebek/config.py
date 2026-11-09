"""Uygulama yolları ve yerel günlük yapılandırması."""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

APP_NAME = "Kelebek Sinav Sistemi"


def get_data_dir() -> Path:
    """İşletim sistemine uygun kullanıcı veri dizinini döndür."""
    override = os.environ.get("KELEBEK_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        return base / APP_NAME

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg_data_home) if xdg_data_home else Path.home() / ".local" / "share"
    return base / "kelebek-sinav-sistemi"


def get_database_path() -> Path:
    """SQLite veritabanının kullanıcı veri klasöründeki yolunu döndür."""
    return get_data_dir() / "kelebek.sqlite3"


def configure_logging(app_logger: logging.Logger) -> None:
    """Günlükleri öğrenci verilerinden ayrı kullanıcı veri dizinine yaz."""
    log_dir = get_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_path = log_dir / "application.log"
    for handler in list(app_logger.handlers):
        if not getattr(handler, "_kelebek_handler", False):
            continue
        # Flask'ın app.logger'ı modül adına bağlı olduğundan süreç içinde paylaşılır.
        # Veri klasörü değiştiyse eski dosyaya yazmaya devam etmek yerine kapatılır.
        if Path(getattr(handler, "baseFilename", "")) == log_path.resolve():
            return
        app_logger.removeHandler(handler)
        handler.close()

    handler = RotatingFileHandler(
        log_path,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler._kelebek_handler = True  # type: ignore[attr-defined]
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    app_logger.addHandler(handler)
    app_logger.setLevel(logging.INFO)
