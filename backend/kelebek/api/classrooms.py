"""Derslik ve düzen kayıtlarını yöneten yerel API."""

from flask import Blueprint, current_app, jsonify, request
from math import isfinite
from sqlalchemy import func, select

from kelebek.db import current_academic_year_start
from kelebek.models import AcademicYear, Classroom, ClassroomLayout, Desk, Seat


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


def _layout_detail(session, layout):
    desks = session.scalars(
        select(Desk).where(Desk.layout_id == layout.id).order_by(Desk.y, Desk.x)
    ).all()
    result = []
    for desk in desks:
        seats = session.scalars(
            select(Seat).where(Seat.desk_id == desk.id).order_by(Seat.seat_index)
        ).all()
        result.append(
            {
                "id": desk.id,
                "label": desk.label,
                "block_label": desk.block_label,
                "x": desk.x,
                "y": desk.y,
                "rotation_degrees": desk.rotation_degrees,
                "seats": [
                    {
                        "id": seat.id,
                        "seat_number": seat.seat_number,
                        "seat_index": seat.seat_index,
                        "is_available": seat.is_available,
                        "x": seat.x,
                        "y": seat.y,
                    }
                    for seat in seats
                ],
            }
        )
    return {"layout": _layout_payload(session, layout), "desks": result}


def _is_archive_layout(session, layout):
    if not layout.academic_year_id:
        return False
    year = session.get(AcademicYear, layout.academic_year_id)
    return year is not None and year.start_year < current_academic_year_start()


def _is_latest_layout_version(session, layout):
    query = select(func.max(ClassroomLayout.version)).where(
        ClassroomLayout.classroom_id == layout.classroom_id,
        ClassroomLayout.name == layout.name,
        ClassroomLayout.academic_year_id == layout.academic_year_id,
    )
    return layout.version == session.scalar(query)


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


@classrooms_api.get("/classrooms/<classroom_id>/layouts/<layout_id>")
def get_classroom_layout(classroom_id: str, layout_id: str):
    """Bir düzenin fiziksel masa ve oturma yeri görünümünü döndür."""
    session_factory = current_app.extensions["kelebek_session_factory"]
    with session_factory() as session:
        layout = session.get(ClassroomLayout, layout_id)
        if layout is None or layout.classroom_id != classroom_id:
            return jsonify({"error": "Derslik düzeni bulunamadı."}), 404
        response = _layout_detail(session, layout)
    return jsonify(response)


@classrooms_api.post("/classrooms/<classroom_id>/layouts/<layout_id>/versions")
def create_layout_version(classroom_id: str, layout_id: str):
    """Düzenlemeden önce mevcut planı koruyup yeni sürüme kopyala."""
    session_factory = current_app.extensions["kelebek_session_factory"]
    with session_factory.begin() as session:
        source = session.get(ClassroomLayout, layout_id)
        if source is None or source.classroom_id != classroom_id:
            return jsonify({"error": "Derslik düzeni bulunamadı."}), 404
        if _is_archive_layout(session, source):
            return jsonify({"error": "Arşiv yılı düzenleri salt okunur."}), 403
        if not _is_latest_layout_version(session, source):
            return jsonify({"error": "Yeni sürüm yalnızca son düzen sürümünden başlatılabilir."}), 409

        version = session.scalar(
            select(func.max(ClassroomLayout.version)).where(
                ClassroomLayout.classroom_id == source.classroom_id,
                ClassroomLayout.name == source.name,
                ClassroomLayout.academic_year_id == source.academic_year_id,
            )
        ) or source.version
        updated = ClassroomLayout(
            classroom_id=source.classroom_id,
            academic_year_id=source.academic_year_id,
            name=source.name,
            version=version + 1,
        )
        session.add(updated)
        session.flush()

        source_desks = session.scalars(
            select(Desk).where(Desk.layout_id == source.id).order_by(Desk.y, Desk.x)
        ).all()
        for source_desk in source_desks:
            desk = Desk(
                layout_id=updated.id,
                label=source_desk.label,
                block_label=source_desk.block_label,
                x=source_desk.x,
                y=source_desk.y,
                rotation_degrees=source_desk.rotation_degrees,
            )
            session.add(desk)
            session.flush()
            source_seats = session.scalars(
                select(Seat).where(Seat.desk_id == source_desk.id).order_by(Seat.seat_index)
            ).all()
            for source_seat in source_seats:
                session.add(
                    Seat(
                        layout_id=updated.id,
                        desk_id=desk.id,
                        seat_number=source_seat.seat_number,
                        seat_index=source_seat.seat_index,
                        x=source_seat.x,
                        y=source_seat.y,
                        is_available=source_seat.is_available,
                        unavailable_reason=source_seat.unavailable_reason,
                    )
                )
        session.flush()
        response = _layout_detail(session, updated)
    return jsonify(response), 201


@classrooms_api.patch("/classrooms/<classroom_id>/layouts/<layout_id>/desks/<desk_id>")
def move_layout_desk(classroom_id: str, layout_id: str, desk_id: str):
    """Masayı yeni koordinata taşı ve ona bağlı koltukları birlikte kaydır."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Yeni masa konumu gerekli."}), 400
    x, y = payload.get("x"), payload.get("y")
    if (
        isinstance(x, bool)
        or isinstance(y, bool)
        or not isinstance(x, (int, float))
        or not isinstance(y, (int, float))
        or not isfinite(x)
        or not isfinite(y)
        or not 0 <= x <= 1000
        or not 0 <= y <= 1000
    ):
        return jsonify({"error": "Masa konumu geçersiz."}), 400

    session_factory = current_app.extensions["kelebek_session_factory"]
    with session_factory.begin() as session:
        layout = session.get(ClassroomLayout, layout_id)
        desk = session.get(Desk, desk_id)
        if layout is None or layout.classroom_id != classroom_id or desk is None or desk.layout_id != layout_id:
            return jsonify({"error": "Masa veya derslik düzeni bulunamadı."}), 404
        if _is_archive_layout(session, layout):
            return jsonify({"error": "Arşiv yılı düzenleri salt okunur."}), 403
        if not _is_latest_layout_version(session, layout):
            return jsonify({"error": "Önce bu düzenin yeni bir sürümünü oluşturun."}), 409

        x, y = float(x), float(y)
        others = session.scalars(
            select(Desk).where(Desk.layout_id == layout_id, Desk.id != desk_id)
        ).all()
        if any(abs(other.x - x) < 1.4 and abs(other.y - y) < 0.9 for other in others):
            return jsonify({"error": "Bu konum başka bir masayla çakışıyor."}), 409

        delta_x, delta_y = x - desk.x, y - desk.y
        desk.x, desk.y = x, y
        seats = session.scalars(select(Seat).where(Seat.desk_id == desk_id)).all()
        for seat in seats:
            seat.x += delta_x
            seat.y += delta_y
        session.flush()
        response = {
            "id": desk.id,
            "x": desk.x,
            "y": desk.y,
            "seats": [{"id": seat.id, "x": seat.x, "y": seat.y} for seat in seats],
        }
    return jsonify({"desk": response})


@classrooms_api.patch("/classrooms/<classroom_id>/layouts/<layout_id>/seats/<seat_id>")
def set_layout_seat_availability(classroom_id: str, layout_id: str, seat_id: str):
    """Oturma yerini kullanılabilir veya kapalı olarak kaydet."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or type(payload.get("is_available")) is not bool:
        return jsonify({"error": "Oturma yeri durumu geçersiz."}), 400
    reason = payload.get("unavailable_reason")
    if reason is not None and not isinstance(reason, str):
        return jsonify({"error": "Kapatma açıklaması metin olmalı."}), 400
    reason = reason.strip() if isinstance(reason, str) else ""
    if len(reason) > 240:
        return jsonify({"error": "Kapatma açıklaması 240 karakterden kısa olmalı."}), 400

    session_factory = current_app.extensions["kelebek_session_factory"]
    with session_factory.begin() as session:
        layout = session.get(ClassroomLayout, layout_id)
        seat = session.get(Seat, seat_id)
        if layout is None or layout.classroom_id != classroom_id or seat is None or seat.layout_id != layout_id:
            return jsonify({"error": "Oturma yeri veya derslik düzeni bulunamadı."}), 404
        if _is_archive_layout(session, layout):
            return jsonify({"error": "Arşiv yılı düzenleri salt okunur."}), 403
        if not _is_latest_layout_version(session, layout):
            return jsonify({"error": "Önce bu düzenin yeni bir sürümünü oluşturun."}), 409
        seat.is_available = payload["is_available"]
        seat.unavailable_reason = reason or None if not seat.is_available else None
        session.flush()
        result = {
            "id": seat.id,
            "is_available": seat.is_available,
            "unavailable_reason": seat.unavailable_reason,
        }
    return jsonify({"seat": result})


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


@classrooms_api.post("/classrooms/<classroom_id>/layouts/<layout_id>/generate")
def generate_classroom_layout(classroom_id: str, layout_id: str):
    """Parametrelerden başlangıç blok/masa/oturma yeri planı oluştur."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Düzen ölçüleri gerekli."}), 400
    rows = payload.get("rows")
    block_sizes = payload.get("block_sizes")
    seats_per_desk = payload.get("seats_per_desk")
    if type(rows) is not int or not 1 <= rows <= 40:
        return jsonify({"error": "Satır sayısı 1 ile 40 arasında olmalı."}), 400
    if (
        not isinstance(block_sizes, list)
        or not block_sizes
        or any(type(size) is not int or not 1 <= size <= 80 for size in block_sizes)
    ):
        return jsonify({"error": "Blok başına masa sayılarını pozitif tam sayılarla girin."}), 400
    if type(seats_per_desk) is not int or seats_per_desk not in {1, 2, 3}:
        return jsonify({"error": "Masa başına oturma yeri sayısı 1, 2 veya 3 olabilir."}), 400
    total_seats = rows * sum(block_sizes) * seats_per_desk
    if total_seats > 600:
        return jsonify({"error": "Bir düzen en fazla 600 oturma yeri içerebilir."}), 400

    session_factory = current_app.extensions["kelebek_session_factory"]
    with session_factory.begin() as session:
        layout = session.get(ClassroomLayout, layout_id)
        if layout is None or layout.classroom_id != classroom_id:
            return jsonify({"error": "Derslik düzeni bulunamadı."}), 404
        if layout.academic_year_id:
            academic_year = session.get(AcademicYear, layout.academic_year_id)
            if academic_year and academic_year.start_year < current_academic_year_start():
                return jsonify({"error": "Arşiv yılı düzenleri salt okunur."}), 403
        if not _is_latest_layout_version(session, layout):
            return jsonify({"error": "Önce bu düzenin yeni bir sürümünü oluşturun."}), 409
        if session.scalar(select(func.count(Desk.id)).where(Desk.layout_id == layout_id)):
            return jsonify({"error": "Bu düzende masalar var. Yeni bir düzen sürümü oluşturarak devam edin."}), 409

        seat_number = 1
        desk_counter = 0
        row_spacing = 2.0
        desk_spacing = 2.0
        aisle_spacing = 2.6
        for row_index in range(rows):
            x_cursor = 0.0
            row_desk_counter = 0
            for block_index, desk_count in enumerate(block_sizes):
                if block_index:
                    x_cursor += aisle_spacing
                for _desk_index in range(desk_count):
                    desk_counter += 1
                    row_desk_counter += 1
                    desk = Desk(
                        layout_id=layout_id,
                        label=f"S{row_index + 1}-M{row_desk_counter}",
                        block_label=f"B{block_index + 1}",
                        x=x_cursor,
                        y=row_index * row_spacing,
                        rotation_degrees=0,
                    )
                    session.add(desk)
                    session.flush()
                    for seat_index in range(1, seats_per_desk + 1):
                        session.add(
                            Seat(
                                layout_id=layout_id,
                                desk_id=desk.id,
                                seat_number=seat_number,
                                seat_index=seat_index,
                                x=x_cursor + 0.25 + (seat_index - 1) * 0.45,
                                y=row_index * row_spacing,
                                is_available=True,
                            )
                        )
                        seat_number += 1
                    x_cursor += desk_spacing
        session.flush()
        response = _layout_payload(session, layout)
    return jsonify({"layout": response, "desk_count": desk_counter, "seat_count": total_seats}), 201
