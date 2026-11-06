"""Eğitim-öğretim yılı listeleme ve seçme uç noktaları."""

from flask import Blueprint, abort, current_app, jsonify, request
from sqlalchemy import select, update

from kelebek.db import current_academic_year_start
from kelebek.models import AcademicYear


academic_year_api = Blueprint("academic_years", __name__)


def _serialize_year(year: AcademicYear, current_start_year: int) -> dict:
    return {
        "id": year.id,
        "label": year.label,
        "start_year": year.start_year,
        "end_year": year.end_year,
        "is_selected": year.is_selected,
        "is_current": year.start_year == current_start_year,
        "is_archive": year.start_year < current_start_year,
    }


@academic_year_api.get("/academic-years")
def list_academic_years():
    """Kayıtlı eğitim yıllarını ve varsayılan seçimi döndür."""
    session_factory = current_app.extensions["kelebek_session_factory"]
    current_start_year = current_academic_year_start()

    with session_factory() as session:
        years = session.scalars(
            select(AcademicYear).order_by(AcademicYear.start_year.desc())
        ).all()

    serialized = [_serialize_year(year, current_start_year) for year in years]
    selected = next((year for year in serialized if year["is_selected"]), None)
    return jsonify(
        {
            "years": serialized,
            "selected_academic_year_id": selected["id"] if selected else None,
            "current_label": f"{current_start_year}-{current_start_year + 1}",
        }
    )


@academic_year_api.put("/academic-years/active")
def select_academic_year():
    """Kullanıcının onayladığı eğitim yılını seçili çalışma yılı yap."""
    payload = request.get_json(silent=True)
    year_id = payload.get("academic_year_id") if isinstance(payload, dict) else None
    if not isinstance(year_id, str) or not year_id:
        return jsonify({"error": "academic_year_id alanı gereklidir."}), 400

    session_factory = current_app.extensions["kelebek_session_factory"]
    current_start_year = current_academic_year_start()

    with session_factory.begin() as session:
        year = session.get(AcademicYear, year_id)
        if year is None:
            abort(404, description="Eğitim-öğretim yılı bulunamadı.")

        session.execute(update(AcademicYear).values(is_selected=False))
        year.is_selected = True
        session.flush()
        result = _serialize_year(year, current_start_year)

    return jsonify({"selected_year": result})
