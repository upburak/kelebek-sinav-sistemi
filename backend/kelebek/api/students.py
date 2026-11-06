"""Seçili eğitim-öğretim yılının öğrenci kayıt API'si."""

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import IntegrityError

from kelebek.models import AcademicYear
from kelebek.services.student_registry import (
    StudentRegistryError,
    add_student_to_year,
    list_year_students,
)


students_api = Blueprint("students", __name__)


@students_api.get("/students")
def get_students():
    academic_year_id = request.args.get("academic_year_id", "").strip()
    if not academic_year_id:
        return jsonify({"error": "Eğitim-öğretim yılı gerekli."}), 400
    session_factory = current_app.extensions["kelebek_session_factory"]
    with session_factory() as session:
        if session.get(AcademicYear, academic_year_id) is None:
            return jsonify({"error": "Seçili eğitim-öğretim yılı bulunamadı."}), 404
        students = list_year_students(session, academic_year_id)
    return jsonify({"students": students, "total": len(students)})


@students_api.post("/students")
def create_student():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Öğrenci bilgileri JSON biçiminde gönderilmelidir."}), 400
    academic_year_id = payload.get("academic_year_id")
    if not isinstance(academic_year_id, str) or not academic_year_id.strip():
        return jsonify({"error": "Eğitim-öğretim yılı gerekli."}), 400

    session_factory = current_app.extensions["kelebek_session_factory"]
    try:
        with session_factory.begin() as session:
            student = add_student_to_year(session, academic_year_id.strip(), payload)
    except StudentRegistryError as error:
        return jsonify({"error": str(error)}), error.status_code
    except IntegrityError:
        return jsonify({"error": "Kayıt aynı anda değişti; okul numarasını kontrol edip yeniden deneyin."}), 409
    return jsonify({"student": student}), 201
