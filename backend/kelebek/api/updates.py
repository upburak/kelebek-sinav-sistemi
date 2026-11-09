"""Artımlı güncelleme API'si: paket önizleme, iptal ve onaylı uygulama."""

import logging
import threading

from flask import Blueprint, current_app, jsonify, request

from kelebek.services import app_update
from kelebek.services.backup import create_safety_backup

updates_api = Blueprint("updates", __name__)
logger = logging.getLogger(__name__)


@updates_api.get("/updates/status")
def get_update_status():
    return jsonify(app_update.status())


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
