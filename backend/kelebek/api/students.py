"""Seçili eğitim-öğretim yılının öğrenci kayıt API'si."""

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import IntegrityError

from kelebek.models import AcademicYear
from kelebek.services.student_registry import (
    StudentRegistryError,
    add_student_to_year,
    deactivate_student_in_year,
    list_year_student_groups,
    list_year_students,
    reactivate_student_in_year,
    update_student_in_year,
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
        students = list_year_students(
            session,
            academic_year_id,
            include_inactive=request.args.get("include_inactive") == "true",
        )
    return jsonify({"students": students, "total": len(students)})


@students_api.get("/student-groups")
def get_student_groups():
    academic_year_id = request.args.get("academic_year_id", "").strip()
    if not academic_year_id:
        return jsonify({"error": "Eğitim-öğretim yılı gerekli."}), 400
    session_factory = current_app.extensions["kelebek_session_factory"]
    with session_factory() as session:
        if session.get(AcademicYear, academic_year_id) is None:
            return jsonify({"error": "Seçili eğitim-öğretim yılı bulunamadı."}), 404
        groups = list_year_student_groups(session, academic_year_id)
    return jsonify({"groups": groups})


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


@students_api.patch("/students/<enrollment_id>")
def update_student(enrollment_id: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Düzenleme bilgileri JSON biçiminde gönderilmelidir."}), 400
    academic_year_id = payload.get("academic_year_id")
    session_factory = current_app.extensions["kelebek_session_factory"]
    try:
        with session_factory.begin() as session:
            from kelebek.models import StudentYearEnrollment

            enrollment = session.get(StudentYearEnrollment, enrollment_id)
            if enrollment is None or enrollment.academic_year_id != academic_year_id:
                return jsonify({"error": "Öğrenci seçili eğitim yılında bulunamadı."}), 404
            if not enrollment.is_active:
                return jsonify({"error": "Pasif öğrenci doğrudan düzenlenemez."}), 409
            student = update_student_in_year(session, enrollment, payload)
    except StudentRegistryError as error:
        return jsonify({"error": str(error)}), error.status_code
    except IntegrityError:
        return jsonify({"error": "Kayıt aynı anda değişti; bilgileri kontrol edip yeniden deneyin."}), 409
    return jsonify({"student": student})


@students_api.post("/students/<enrollment_id>/deactivate")
def deactivate_student(enrollment_id: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or payload.get("confirmed") is not True:
        return jsonify({"error": "Öğrenciyi pasife almak için uygulama içi açık onay gereklidir."}), 400
    academic_year_id = payload.get("academic_year_id")
    session_factory = current_app.extensions["kelebek_session_factory"]
    try:
        with session_factory.begin() as session:
            from kelebek.models import StudentYearEnrollment

            enrollment = session.get(StudentYearEnrollment, enrollment_id)
            if enrollment is None or enrollment.academic_year_id != academic_year_id:
                return jsonify({"error": "Öğrenci seçili eğitim yılında bulunamadı."}), 404
            deactivate_student_in_year(session, enrollment)
    except StudentRegistryError as error:
        return jsonify({"error": str(error)}), error.status_code
    return jsonify({"deactivated": True, "history_preserved": True})


@students_api.post("/students/<enrollment_id>/reactivate")
def reactivate_student(enrollment_id: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or payload.get("confirmed") is not True:
        return jsonify({"error": "Öğrenciyi yeniden etkinleştirmek için açık onay gereklidir."}), 400
    academic_year_id = payload.get("academic_year_id")
    session_factory = current_app.extensions["kelebek_session_factory"]
    try:
        with session_factory.begin() as session:
            from kelebek.models import StudentYearEnrollment

            enrollment = session.get(StudentYearEnrollment, enrollment_id)
            if enrollment is None or enrollment.academic_year_id != academic_year_id:
                return jsonify({"error": "Öğrenci seçili eğitim yılında bulunamadı."}), 404
            student = reactivate_student_in_year(session, enrollment)
    except StudentRegistryError as error:
        return jsonify({"error": str(error)}), error.status_code
    except IntegrityError:
        return jsonify({"error": "Öğrenci yeniden etkinleştirilemedi; numarayı kontrol edin."}), 409
    return jsonify({"student": student})
