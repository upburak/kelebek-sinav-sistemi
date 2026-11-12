"""Toplu silme API'si: önizleme ve onaylı silme."""

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import IntegrityError

from kelebek.services import bulk_delete
from kelebek.services.backup import create_safety_backup

bulk_delete_api = Blueprint("bulk_delete", __name__)


@bulk_delete_api.get("/bulk-delete/preview")
def preview_bulk_delete():
    session_factory = current_app.extensions["kelebek_session_factory"]
    try:
        with session_factory() as session:
            counts = bulk_delete.preview(
                session, request.args.get("scope", ""), request.args.get("academic_year_id", ""))
    except bulk_delete.BulkDeleteError as error:
        return jsonify({"error": str(error)}), error.status_code
    return jsonify({"counts": counts})


@bulk_delete_api.post("/bulk-delete")
def run_bulk_delete():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or payload.get("confirm") is not True:
        return jsonify({"error": "Toplu silme için açık onay gereklidir."}), 400
    scope, academic_year_id = payload.get("scope"), payload.get("academic_year_id")
    if not isinstance(scope, str) or not isinstance(academic_year_id, str):
        return jsonify({"error": "Silme kapsamı ve eğitim-öğretim yılı gerekli."}), 400
    session_factory = current_app.extensions["kelebek_session_factory"]
    try:
        with session_factory() as session:
            bulk_delete.preview(session, scope, academic_year_id)   # kapsam ve yıl denetimi
        # Yanlış silme geri alınabilsin: silmeden önce veriler yedeklenir.
        safety_backup = create_safety_backup("bulk-delete")
        with session_factory.begin() as session:
            deleted = bulk_delete.delete_scope(session, scope, academic_year_id)
    except bulk_delete.BulkDeleteError as error:
        return jsonify({"error": str(error)}), error.status_code
    except IntegrityError:
        return jsonify({"error": "Kayıtlar aynı anda değişti; silme yapılmadı. Sayfayı yenileyip tekrar deneyin."}), 409
    return jsonify({"deleted": deleted, "safety_backup": safety_backup.name})
