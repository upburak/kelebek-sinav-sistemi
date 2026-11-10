"""Sınav dönemleri: listeleme, ekleme, yeniden adlandırma ve boş dönemi silme."""

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from kelebek.db import current_academic_year_start, ensure_default_exam_periods
from kelebek.models import AcademicYear, ExamOrganization, ExamPeriod

exam_periods_api = Blueprint("exam_periods_api", __name__)

MAX_NAME_LENGTH = 80
MAX_PERIODS_PER_YEAR = 20


def _clean_name(raw) -> str:
    return " ".join(str(raw or "").strip().split())


def _serialize(period: ExamPeriod, exam_count: int) -> dict:
    return {
        "id": period.id,
        "academic_year_id": period.academic_year_id,
        "name": period.name,
        "display_order": period.display_order,
        "exam_count": exam_count,
        "can_delete": exam_count == 0,
    }


def _year_or_error(session, academic_year_id: str):
    year = session.get(AcademicYear, academic_year_id) if academic_year_id else None
    if year is None:
        return None, (jsonify({"error": "Seçili eğitim-öğretim yılı bulunamadı."}), 404)
    return year, None


def _exam_counts(session, period_ids: list[str]) -> dict[str, int]:
    if not period_ids:
        return {}
    rows = session.execute(
        select(ExamOrganization.exam_period_id, func.count(ExamOrganization.id))
        .where(ExamOrganization.exam_period_id.in_(period_ids))
        .group_by(ExamOrganization.exam_period_id)
    ).all()
    return {period_id: count for period_id, count in rows}


@exam_periods_api.get("/exam-periods")
def list_exam_periods():
    academic_year_id = request.args.get("academic_year_id", "").strip()
    if not academic_year_id:
        return jsonify({"error": "Eğitim-öğretim yılı gerekli."}), 400

    session_factory = current_app.extensions["kelebek_session_factory"]
    with session_factory.begin() as session:
        year, error = _year_or_error(session, academic_year_id)
        if error:
            return error
        # Yıl 0018 öncesinden geliyorsa veya dönemleri silinmişse hazır dönemleri kur.
        ensure_default_exam_periods(session, year.id)
        session.flush()
        periods = session.scalars(
            select(ExamPeriod)
            .where(ExamPeriod.academic_year_id == year.id)
            .order_by(ExamPeriod.display_order, ExamPeriod.created_at)
        ).all()
        counts = _exam_counts(session, [item.id for item in periods])
        result = [_serialize(item, counts.get(item.id, 0)) for item in periods]
    return jsonify({"periods": result})


@exam_periods_api.post("/exam-periods")
def create_exam_period():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Dönem bilgileri JSON biçiminde gönderilmelidir."}), 400
    academic_year_id = str(payload.get("academic_year_id", "")).strip()
    name = _clean_name(payload.get("name"))
    if not name:
        return jsonify({"error": "Dönem adı gerekli."}), 400
    if len(name) > MAX_NAME_LENGTH:
        return jsonify({"error": f"Dönem adı {MAX_NAME_LENGTH} karakterden kısa olmalı."}), 400

    session_factory = current_app.extensions["kelebek_session_factory"]
    try:
        with session_factory.begin() as session:
            year, error = _year_or_error(session, academic_year_id)
            if error:
                return error
            if year.start_year < current_academic_year_start():
                return jsonify({"error": "Arşiv yılına dönem eklenemez."}), 403
            existing = session.scalars(
                select(ExamPeriod).where(ExamPeriod.academic_year_id == year.id)
            ).all()
            if len(existing) >= MAX_PERIODS_PER_YEAR:
                return jsonify({"error": f"Bir yılda en fazla {MAX_PERIODS_PER_YEAR} dönem olabilir."}), 400
            if any(item.name.casefold() == name.casefold() for item in existing):
                return jsonify({"error": "Bu dönem adı zaten var."}), 409
            period = ExamPeriod(
                academic_year_id=year.id,
                name=name,
                display_order=max((item.display_order for item in existing), default=-1) + 1,
            )
            session.add(period)
            session.flush()
            result = _serialize(period, 0)
    except IntegrityError:
        return jsonify({"error": "Dönem aynı anda değişti; listeyi yenileyip tekrar deneyin."}), 409
    return jsonify({"period": result}), 201


@exam_periods_api.patch("/exam-periods/<period_id>")
def rename_exam_period(period_id: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Dönem bilgileri JSON biçiminde gönderilmelidir."}), 400
    name = _clean_name(payload.get("name"))
    if not name:
        return jsonify({"error": "Dönem adı gerekli."}), 400
    if len(name) > MAX_NAME_LENGTH:
        return jsonify({"error": f"Dönem adı {MAX_NAME_LENGTH} karakterden kısa olmalı."}), 400

    session_factory = current_app.extensions["kelebek_session_factory"]
    try:
        with session_factory.begin() as session:
            period = session.get(ExamPeriod, period_id)
            if period is None:
                return jsonify({"error": "Dönem bulunamadı."}), 404
            year = session.get(AcademicYear, period.academic_year_id)
            if year and year.start_year < current_academic_year_start():
                return jsonify({"error": "Arşiv yılı salt okunur."}), 403
            clash = session.scalar(
                select(ExamPeriod).where(
                    ExamPeriod.academic_year_id == period.academic_year_id,
                    ExamPeriod.id != period.id,
                    func.lower(ExamPeriod.name) == name.casefold(),
                )
            )
            if clash is not None:
                return jsonify({"error": "Bu dönem adı zaten var."}), 409
            period.name = name
            session.flush()
            counts = _exam_counts(session, [period.id])
            result = _serialize(period, counts.get(period.id, 0))
    except IntegrityError:
        return jsonify({"error": "Dönem aynı anda değişti; listeyi yenileyip tekrar deneyin."}), 409
    return jsonify({"period": result})


@exam_periods_api.delete("/exam-periods/<period_id>")
def delete_exam_period(period_id: str):
    session_factory = current_app.extensions["kelebek_session_factory"]
    with session_factory.begin() as session:
        period = session.get(ExamPeriod, period_id)
        if period is None:
            return jsonify({"error": "Dönem bulunamadı."}), 404
        year = session.get(AcademicYear, period.academic_year_id)
        if year and year.start_year < current_academic_year_start():
            return jsonify({"error": "Arşiv yılı salt okunur."}), 403
        counts = _exam_counts(session, [period.id])
        if counts.get(period.id, 0):
            return jsonify({
                "error": "Bu dönemde sınav var. Önce sınavları başka bir döneme taşıyın veya silin.",
            }), 409
        session.delete(period)
    return jsonify({"deleted": True})
