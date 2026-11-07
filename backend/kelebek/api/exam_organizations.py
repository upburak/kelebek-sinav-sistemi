"""Sınav organizasyonu taslakları ve ders kataloğu API'si."""

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import IntegrityError

from kelebek.models import AcademicYear
from kelebek.services.exam_organizer import (
    ExamOrganizerError,
    create_organization,
    list_courses,
    list_organizations,
)


exam_organizations_api = Blueprint("exam_organizations", __name__)


@exam_organizations_api.get("/courses")
def get_courses():
    session_factory = current_app.extensions["kelebek_session_factory"]
    with session_factory() as session:
        courses = list_courses(session)
    return jsonify({"courses": courses})


@exam_organizations_api.get("/exam-organizations")
def get_exam_organizations():
    academic_year_id = request.args.get("academic_year_id", "").strip()
    if not academic_year_id:
        return jsonify({"error": "Eğitim-öğretim yılı gerekli."}), 400
    session_factory = current_app.extensions["kelebek_session_factory"]
    with session_factory() as session:
        if session.get(AcademicYear, academic_year_id) is None:
            return jsonify({"error": "Seçili eğitim-öğretim yılı bulunamadı."}), 404
        organizations = list_organizations(session, academic_year_id)
    return jsonify({"organizations": organizations})


@exam_organizations_api.post("/exam-organizations")
def post_exam_organization():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Organizasyon bilgileri JSON biçiminde gönderilmelidir."}), 400
    session_factory = current_app.extensions["kelebek_session_factory"]
    try:
        with session_factory.begin() as session:
            organization = create_organization(session, payload)
    except ExamOrganizerError as error:
        return jsonify({"error": str(error)}), error.status_code
    except IntegrityError:
        return jsonify({"error": "Organizasyon bilgileri aynı anda değişti; seçimleri kontrol edip yeniden deneyin."}), 409
    return jsonify({"organization": organization}), 201
