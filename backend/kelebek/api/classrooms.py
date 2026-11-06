"""Derslik ve düzen kayıtlarını yöneten yerel API."""

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import func, select

from kelebek.db import current_academic_year_start
from kelebek.models import AcademicYear, Classroom, ClassroomLayout, Seat


classrooms_api = Blueprint("classrooms", __name__)


def _layout_payload(session, layout):
    total_seats = session.scalar(
        select(func.count(Seat.id)).where(Seat.layout_id == layout.id)
    ) or 0
    available_seats = session.scalar(
        select(func.count(Seat.id)).where(
            Seat.layout_id == layout.id,
            Seat.is_available.is_(True),
        )
    ) or 0
    year = session.get(AcademicYear, layout.academic_year_id) if layout.academic_year_id else None
    return {
        "id": layout.id,
        "name": layout.name,
        "version": layout.version,
        "academic_year_id": layout.academic_year_id,
        "academic_year_label": year.label if year else None,
        "is_template": layout.academic_year_id is None,
        "total_seats": total_seats,
        "available_seats": available_seats,
    }


@classrooms_api.get("/classrooms")
def list_classrooms():
    """Derslikleri ve kayıtlı düzen sayılarını döndür."""
    session_factory = current_app.extensions["kelebek_session_factory"]
    with session_factory() as session:
        classrooms = session.scalars(select(Classroom).order_by(Classroom.name)).all()
        result = []
        for classroom in classrooms:
            layout_count = session.scalar(
                select(func.count(ClassroomLayout.id)).where(
                    ClassroomLayout.classroom_id == classroom.id
                )
            ) or 0
            result.append({"id": classroom.id, "name": classroom.name, "layout_count": layout_count})
    return jsonify({"classrooms": result})


@classrooms_api.post("/classrooms")
def create_classroom():
    """Yeni fiziksel derslik ekle."""
    payload = request.get_json(silent=True)
    name = payload.get("name") if isinstance(payload, dict) else None
    name = name.strip() if isinstance(name, str) else ""
    if not name:
        return jsonify({"error": "Derslik adı gerekli."}), 400
    if len(name) > 120:
        return jsonify({"error": "Derslik adı 120 karakterden kısa olmalı."}), 400

    session_factory = current_app.extensions["kelebek_session_factory"]
    with session_factory.begin() as session:
        duplicates = session.scalars(select(Classroom)).all()
        if any(item.name.casefold() == name.casefold() for item in duplicates):
            return jsonify({"error": "Bu derslik adı zaten kayıtlı."}), 409
        classroom = Classroom(name=name)
        session.add(classroom)
        session.flush()
        result = {"id": classroom.id, "name": classroom.name, "layout_count": 0}
    return jsonify({"classroom": result}), 201


@classrooms_api.get("/classrooms/<classroom_id>/layouts")
def list_classroom_layouts(classroom_id: str):
    """Bir dersliğe ait yıl düzenlerini ve tekrar kullanılabilir şablonları döndür."""
    session_factory = current_app.extensions["kelebek_session_factory"]
    with session_factory() as session:
        classroom = session.get(Classroom, classroom_id)
        if classroom is None:
            return jsonify({"error": "Derslik bulunamadı."}), 404
        layouts = session.scalars(
            select(ClassroomLayout)
            .where(ClassroomLayout.classroom_id == classroom_id)
            .order_by(ClassroomLayout.created_at.desc(), ClassroomLayout.version.desc())
        ).all()
        result = [_layout_payload(session, layout) for layout in layouts]
    return jsonify({"layouts": result})


@classrooms_api.post("/classrooms/<classroom_id>/layouts")
def create_classroom_layout(classroom_id: str):
    """Yeni boş yıl düzeni veya tekrar kullanılabilir şablon oluştur."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Düzen bilgisi gerekli."}), 400
    name = payload.get("name")
    name = name.strip() if isinstance(name, str) else ""
    if not name:
        return jsonify({"error": "Düzen adı gerekli."}), 400
    if len(name) > 120:
        return jsonify({"error": "Düzen adı 120 karakterden kısa olmalı."}), 400

    is_template = payload.get("is_template") is True
    academic_year_id = None if is_template else payload.get("academic_year_id")
    if not is_template and not isinstance(academic_year_id, str):
        return jsonify({"error": "Bir eğitim-öğretim yılı seçin."}), 400

    session_factory = current_app.extensions["kelebek_session_factory"]
    with session_factory.begin() as session:
        classroom = session.get(Classroom, classroom_id)
        if classroom is None:
            return jsonify({"error": "Derslik bulunamadı."}), 404
        if academic_year_id:
            academic_year = session.get(AcademicYear, academic_year_id)
            if academic_year is None:
                return jsonify({"error": "Eğitim-öğretim yılı bulunamadı."}), 404
            if academic_year.start_year < current_academic_year_start():
                return jsonify({"error": "Arşiv yıllarına derslik düzeni eklenemez."}), 403

        version_query = select(func.max(ClassroomLayout.version)).where(
            ClassroomLayout.classroom_id == classroom_id,
            ClassroomLayout.name == name,
        )
        if academic_year_id is None:
            version_query = version_query.where(ClassroomLayout.academic_year_id.is_(None))
        else:
            version_query = version_query.where(ClassroomLayout.academic_year_id == academic_year_id)
        version = (session.scalar(version_query) or 0) + 1

        layout = ClassroomLayout(
            classroom_id=classroom_id,
            academic_year_id=academic_year_id,
            name=name,
            version=version,
        )
        session.add(layout)
        session.flush()
        result = _layout_payload(session, layout)
    return jsonify({"layout": result}), 201
