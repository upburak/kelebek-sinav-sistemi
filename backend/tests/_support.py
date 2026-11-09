"""Testlerin uygulama kaynaklarını bırakması için ortak yardımcı.

Windows açık bir dosyanın silinmesine izin vermediğinden, geçici veri klasörü
temizlenmeden önce uygulamanın SQLite motoru ve günlük dosyası kapatılmalıdır.
Aksi halde testin kendisi `PermissionError: [WinError 32]` ile düşer.
"""

from __future__ import annotations


def release_app_resources(app) -> None:
    """Uygulamanın tuttuğu dosya tutamaklarını kapat (motor + günlük dosyası)."""
    engine = app.extensions.get("kelebek_engine")
    if engine is not None:
        engine.dispose()
    for handler in list(app.logger.handlers):
        if getattr(handler, "_kelebek_handler", False):
            app.logger.removeHandler(handler)
            handler.close()
