"""Artımlı güncelleme API'si: paket önizleme, iptal ve onaylı uygulama."""

import json
import logging
import threading

from flask import Blueprint, current_app, jsonify, request

from kelebek.config import get_data_dir
from kelebek.release_notes import RELEASE_NOTES
from kelebek.services import app_update, online_update
from kelebek.services.backup import create_safety_backup
from kelebek.version import APP_VERSION

updates_api = Blueprint("updates", __name__)
logger = logging.getLogger(__name__)


@updates_api.get("/updates/status")
def get_update_status():
    # Açılış denetimi ayarı buradan okunur; internete çıkmadan hemen döner.
    return jsonify({**app_update.status(), "auto_update_check": _auto_check_enabled()})


def _ui_state_path():
    return get_data_dir() / "ui_state.json"


def _parse_version(value: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in value.split("."))
    except (AttributeError, ValueError):
        return (0,)


@updates_api.get("/app/whats-new")
def get_whats_new():
    """Güncellemeden sonraki ilk açılışta, görülmemiş sürümlerin notlarını döndür."""
    try:
        state = json.loads(_ui_state_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    last_seen = state.get("last_seen_version")
    if last_seen is None:
        _ui_state_path().write_text(json.dumps({**state, "last_seen_version": APP_VERSION}), encoding="utf-8")
        return jsonify({"show": False, "current_version": APP_VERSION, "notes": []})
    notes = [item for item in RELEASE_NOTES
             if _parse_version(last_seen) < _parse_version(item["version"]) <= _parse_version(APP_VERSION)]
    return jsonify({"show": bool(notes), "current_version": APP_VERSION, "previous_version": last_seen, "notes": notes})


@updates_api.get("/app/release-notes")
def get_release_notes():
    """Bu sürüme kadarki tüm sürüm notları (en yeni başta)."""
    return jsonify({"current_version": APP_VERSION, "notes": RELEASE_NOTES})


@updates_api.post("/app/whats-new/seen")
def mark_whats_new_seen():
    try:
        state = json.loads(_ui_state_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    _ui_state_path().write_text(json.dumps({**state, "last_seen_version": APP_VERSION}), encoding="utf-8")
    return jsonify({"seen": APP_VERSION})


@updates_api.post("/updates/inspect")
def inspect_update():
    uploaded = request.files.get("package")
    if uploaded is None or not uploaded.filename:
        return jsonify({"error": "Önizleme için bir güncelleme paketi (ZIP) seçin."}), 400
    try:
        token, summary = app_update.inspect_package(uploaded.stream)
    except app_update.UpdateError as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"token": token, "summary": summary})


@updates_api.post("/updates/cancel")
def cancel_update():
    payload = request.get_json(silent=True) or {}
    return jsonify({"cancelled": app_update.discard(payload.get("token"))})


@updates_api.post("/updates/apply")
def apply_update():
    payload = request.get_json(silent=True) or {}
    if payload.get("confirm") is not True:
        return jsonify({"error": "Güncellemeyi uygulamak için açık onay gereklidir."}), 400
    try:
        if app_update.install_root() is None:
            raise app_update.UpdateError("Güncelleme yalnızca kurulu (paketlenmiş) uygulamada uygulanabilir.")
        safety_backup = create_safety_backup("app-update")
        job = app_update.prepare_apply(payload.get("token"), safety_backup)
        app_update.spawn_updater(job)
    except app_update.UpdateError as error:
        return jsonify({"error": str(error)}), 409
    shutdown = current_app.extensions.get("kelebek_shutdown")
    if shutdown:
        threading.Timer(0.8, shutdown).start()
    return jsonify({"applying": True, "safety_backup": safety_backup.name, "to_version": job["to_version"]})


def _read_ui_state() -> dict:
    try:
        return json.loads(_ui_state_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _auto_check_enabled() -> bool:
    return _read_ui_state().get("auto_update_check", True) is not False


@updates_api.get("/updates/online")
def check_online_update():
    """GitHub'daki son sürümü sor. `auto=1` açılış denetimidir ve ayar kapalıysa internete çıkmaz."""
    enabled = _auto_check_enabled()
    if request.args.get("auto") == "1" and not enabled:
        return jsonify({"checked": False, "auto_check": False, "current_version": APP_VERSION})
    try:
        result = online_update.check_latest()
    except online_update.OnlineUpdateError as error:
        return jsonify({"checked": False, "auto_check": enabled, "current_version": APP_VERSION,
                        "error": str(error)})
    return jsonify({"checked": True, "auto_check": enabled, **result})


@updates_api.put("/updates/online/settings")
def put_online_update_settings():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("auto_check"), bool):
        return jsonify({"error": "Ayar geçersiz."}), 400
    _ui_state_path().write_text(
        json.dumps({**_read_ui_state(), "auto_update_check": payload["auto_check"]}), encoding="utf-8"
    )
    return jsonify({"auto_check": payload["auto_check"]})


@updates_api.post("/updates/online/download")
def download_online_update():
    """Son sürümün kurulum paketini indir, doğrula ve kurulumu başlat."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or payload.get("confirm") is not True:
        return jsonify({"error": "İndirme için açık onay gereklidir."}), 400
    try:
        latest = online_update.check_latest()
        if not latest["update_available"]:
            return jsonify({"error": "Kurulu sürüm zaten güncel."}), 409
        if not latest["asset"]:
            return jsonify({"error": "Bu bilgisayar için kurulum paketi bulunamadı; indirme sayfasını kullanın.",
                            "release_url": latest["release_url"]}), 409
        # Kurulumdan önce veriler yedeklenir (Karar 72); yedek veri klasöründe kalır.
        safety_backup = create_safety_backup("app-update")
        path = online_update.download_package(latest["asset"])
    except online_update.OnlineUpdateError as error:
        return jsonify({"error": str(error)}), 502
    opened = online_update.open_package(path)
    return jsonify({"downloaded": True, "opened": opened, "path": str(path), "version": latest["latest_version"],
                    "safety_backup": safety_backup.name})
