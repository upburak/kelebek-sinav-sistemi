"""Derslik ve düzen kayıtlarını yöneten yerel API."""

from math import isfinite

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from kelebek.db import current_academic_year_start
from kelebek.distribution.neighbors import build_neighbor_pairs
from kelebek.models import (
    AcademicYear,
    Classroom,
    ClassroomLayout,
    Desk,
    ExamOrganizationClassroom,
    Seat,
)
from kelebek.services.exam_organizer import natural_sort_key
from kelebek.services.layouts import (
    activate_layout,
    clone_layout,
    delete_layout,
    ensure_active_layout,
    layout_exam_count,
    layout_finalized_exam_count,
    prepare_layout_for_edit,
)

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
    exam_count = layout_exam_count(session, layout.id)
    return {
        "id": layout.id,
        "name": layout.name,
        "version": layout.version,
        "academic_year_id": layout.academic_year_id,
        "academic_year_label": year.label if year else None,
        "is_template": layout.academic_year_id is None,
        "is_active": bool(layout.is_active),
        "exam_count": exam_count,
        "can_delete": exam_count == 0,
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
            latest_layout_id = session.scalar(
                select(ClassroomLayout.id)
                .where(ClassroomLayout.classroom_id == classroom.id)
                .order_by(ClassroomLayout.is_active.desc(), ClassroomLayout.created_at.desc(),
                          ClassroomLayout.version.desc())
                .limit(1)
            )
            seat_count = 0
            if latest_layout_id:
                seat_count = session.scalar(
                    select(func.count(Seat.id)).where(
                        Seat.layout_id == latest_layout_id, Seat.is_available.is_(True)
                    )
                ) or 0
            result.append({"id": classroom.id, "name": classroom.name, "layout_count": layout_count,
                           "seat_count": seat_count})
    # "9-A" < "10-A": adlardaki sayılar sayı olarak sıralanır.
    result.sort(key=lambda item: natural_sort_key(item["name"]))
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


@classrooms_api.patch("/classrooms/<classroom_id>")
def rename_classroom(classroom_id: str):
    payload = request.get_json(silent=True)
    name = payload.get("name") if isinstance(payload, dict) else None
    name = name.strip() if isinstance(name, str) else ""
    if not name:
        return jsonify({"error": "Derslik adı gerekli."}), 400
    if len(name) > 120:
        return jsonify({"error": "Derslik adı 120 karakterden kısa olmalı."}), 400

    session_factory = current_app.extensions["kelebek_session_factory"]
    with session_factory.begin() as session:
        classroom = session.get(Classroom, classroom_id)
        if classroom is None:
            return jsonify({"error": "Derslik bulunamadı."}), 404
        in_history = session.scalar(select(func.count(ExamOrganizationClassroom.id)).where(
            ExamOrganizationClassroom.classroom_id == classroom_id,
        )) or 0
        if in_history:
            return jsonify({"error": "Bu derslik sınav organizasyonlarında kullanılmış; geçmiş adını korumak için yeniden adlandırılamaz."}), 409
        duplicates = session.scalars(select(Classroom).where(Classroom.id != classroom_id)).all()
        if any(item.name.casefold() == name.casefold() for item in duplicates):
            return jsonify({"error": "Bu derslik adı zaten kayıtlı."}), 409
        classroom.name = name
        result = {"id": classroom.id, "name": classroom.name}
    return jsonify({"classroom": result})


@classrooms_api.delete("/classrooms/<classroom_id>")
def delete_empty_classroom(classroom_id: str):
    session_factory = current_app.extensions["kelebek_session_factory"]
    with session_factory.begin() as session:
        classroom = session.get(Classroom, classroom_id)
        if classroom is None:
            return jsonify({"error": "Derslik bulunamadı."}), 404
        layouts = session.scalar(select(func.count(ClassroomLayout.id)).where(
            ClassroomLayout.classroom_id == classroom_id,
        )) or 0
        organizations = session.scalar(select(func.count(ExamOrganizationClassroom.id)).where(
            ExamOrganizationClassroom.classroom_id == classroom_id,
        )) or 0
        if layouts or organizations:
            return jsonify({
                "error": "Düzeni veya sınav geçmişi bulunan derslik silinemez. Kullanılmayan boş derslikler silinebilir; geçmiş kayıtlar korunur.",
            }), 409
        session.delete(classroom)
    return jsonify({"deleted": True})


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


@classrooms_api.get("/classrooms/<classroom_id>/plan")
def get_classroom_plan(classroom_id: str):
    """Dersliğin seçili yıldaki aktif planını, kullanım sayılarıyla birlikte döndür."""
    academic_year_id = request.args.get("academic_year_id")
    if not academic_year_id:
        return jsonify({"error": "Eğitim-öğretim yılı seçili değil."}), 400
    session_factory = current_app.extensions["kelebek_session_factory"]
    with session_factory() as session:
        classroom = session.get(Classroom, classroom_id)
        if classroom is None:
            return jsonify({"error": "Derslik bulunamadı."}), 404
        active = session.scalars(
            select(ClassroomLayout).where(
                ClassroomLayout.classroom_id == classroom_id,
                ClassroomLayout.academic_year_id == academic_year_id,
                ClassroomLayout.is_active.is_(True),
            ).limit(1)
        ).first()
        layout_total = session.scalar(
            select(func.count(ClassroomLayout.id)).where(ClassroomLayout.classroom_id == classroom_id)
        ) or 0
        plan = None
        if active is not None:
            plan = _layout_detail(session, active)
            plan["exam_count"] = layout_exam_count(session, active.id)
            plan["finalized_exam_count"] = layout_finalized_exam_count(session, active.id)
            plan["read_only"] = _is_archive_layout(session, active)
        result = {
            "classroom": {"id": classroom.id, "name": classroom.name},
            "plan": plan,
            "other_layout_count": layout_total - (1 if active is not None else 0),
        }
    return jsonify(result)


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


@classrooms_api.get("/classrooms/<classroom_id>/layouts/<layout_id>/neighbors")
def get_classroom_layout_neighbors(classroom_id: str, layout_id: str):
    """Izgara konumlarından yan ve ön-arka koltuk komşuluklarını hesapla."""
    session_factory = current_app.extensions["kelebek_session_factory"]
    with session_factory() as session:
        layout = session.get(ClassroomLayout, layout_id)
        if layout is None or layout.classroom_id != classroom_id:
            return jsonify({"error": "Derslik düzeni bulunamadı."}), 404
        desks = session.scalars(select(Desk).where(Desk.layout_id == layout_id)).all()
        graph_input = []
        for desk in desks:
            seats = session.scalars(select(Seat).where(Seat.desk_id == desk.id)).all()
            graph_input.append({
                "id": desk.id,
                "x": desk.x,
                "y": desk.y,
                "block_label": desk.block_label,
                "seats": [
                    {"id": seat.id, "seat_index": seat.seat_index, "is_available": seat.is_available}
                    for seat in seats
                ],
            })
        try:
            pairs = build_neighbor_pairs(graph_input)
        except ValueError as error:
            return jsonify({"error": str(error)}), 409
    return jsonify(pairs)


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

        updated = clone_layout(session, source)
        # Düzenlemek için açılan yeni sürüm, kaynağın aktifliğini devralır.
        if source.is_active:
            activate_layout(session, updated)
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
            return jsonify({"error": "Bu, planın eski bir hâli; güncel planı açıp orada düzenleyin."}), 409
        # Kesinleşmiş sınavda kullanılan plan kopyalanır; değişiklik kopyadaki aynı masaya yazılır.
        target, affected_drafts = prepare_layout_for_edit(session, layout)
        copied = target.id != layout.id
        if copied:
            desk = session.scalar(select(Desk).where(Desk.layout_id == target.id, Desk.label == desk.label))
            layout_id, desk_id = target.id, desk.id

        x, y = float(x), float(y)
        others = session.scalars(
            select(Desk).where(Desk.layout_id == layout_id, Desk.id != desk_id)
        ).all()
        x = round(float(x) / 2.0) * 2.0
        y = round(float(y) / 2.0) * 2.0
        if any(other.x == x and other.y == y for other in others):
            return jsonify({"error": "Bu ızgara hücresi dolu. Başka bir hücre seçin."}), 409
        delta_x, delta_y = x - desk.x, y - desk.y
        desk.x, desk.y = x, y
        seats = session.scalars(select(Seat).where(Seat.desk_id == desk_id)).all()
        for seat in seats:
            seat.x += delta_x
            seat.y += delta_y
        session.flush()
        edit_info = {"layout_id": layout_id, "copied": copied, "affected_draft_exam_count": affected_drafts}
        response = {
            "id": desk.id,
            "x": desk.x,
            "y": desk.y,
            "seats": [{"id": seat.id, "x": seat.x, "y": seat.y} for seat in seats],
        }
    return jsonify({"desk": response, **edit_info})


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
            return jsonify({"error": "Bu, planın eski bir hâli; güncel planı açıp orada düzenleyin."}), 409
        target, affected_drafts = prepare_layout_for_edit(session, layout)
        copied = target.id != layout.id
        if copied:
            seat = session.scalar(
                select(Seat).where(Seat.layout_id == target.id, Seat.seat_number == seat.seat_number)
            )
        seat.is_available = payload["is_available"]
        seat.unavailable_reason = reason or None if not seat.is_available else None
        session.flush()
        edit_info = {"layout_id": target.id, "copied": copied, "affected_draft_exam_count": affected_drafts}
        result = {
            "id": seat.id,
            "is_available": seat.is_available,
            "unavailable_reason": seat.unavailable_reason,
        }
    return jsonify({"seat": result, **edit_info})


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
        ensure_active_layout(session, layout)
        result = _layout_payload(session, layout)
    return jsonify({"layout": result}), 201


@classrooms_api.post("/classrooms/<classroom_id>/layouts/<layout_id>/activate")
def activate_classroom_layout(classroom_id: str, layout_id: str):
    """Sınavlarda varsayılan olarak kullanılacak düzeni belirle."""
    session_factory = current_app.extensions["kelebek_session_factory"]
    with session_factory.begin() as session:
        layout = session.get(ClassroomLayout, layout_id)
        if layout is None or layout.classroom_id != classroom_id:
            return jsonify({"error": "Derslik düzeni bulunamadı."}), 404
        if _is_archive_layout(session, layout):
            return jsonify({"error": "Arşiv yılı düzenleri salt okunur."}), 403
        try:
            activate_layout(session, layout)
        except ValueError as error:
            return jsonify({"error": str(error)}), 409
        result = _layout_payload(session, layout)
    return jsonify({"layout": result})


@classrooms_api.delete("/classrooms/<classroom_id>/layouts/<layout_id>")
def delete_classroom_layout(classroom_id: str, layout_id: str):
    """Hiçbir sınavda kullanılmayan düzeni sil."""
    session_factory = current_app.extensions["kelebek_session_factory"]
    try:
        with session_factory.begin() as session:
            layout = session.get(ClassroomLayout, layout_id)
            if layout is None or layout.classroom_id != classroom_id:
                return jsonify({"error": "Derslik düzeni bulunamadı."}), 404
            if _is_archive_layout(session, layout):
                return jsonify({"error": "Arşiv yılı düzenleri salt okunur."}), 403
            try:
                delete_layout(session, layout)
            except ValueError as error:
                return jsonify({"error": str(error)}), 409
    except IntegrityError:
        return jsonify({
            "error": "Bu düzenin koltukları geçmiş bir dağıtımda kullanılmış; düzen silinemez.",
        }), 409
    return jsonify({"deleted": True})


@classrooms_api.post("/classrooms/<classroom_id>/layouts/<layout_id>/generate")
def generate_classroom_layout(classroom_id: str, layout_id: str):
    """Düzensiz uzunluktaki sütunlardan ızgaralı oturma planı oluştur."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Düzen ölçüleri gerekli."}), 400
    columns = payload.get("columns")
    lengths = payload.get("column_lengths")
    cell_seats = payload.get("cell_seats")
    aisle_after = payload.get("aisle_after", [])
    if type(columns) is not int or not 1 <= columns <= 12:
        return jsonify({"error": "Sütun sayısı 1 ile 12 arasında olmalı."}), 400
    if not isinstance(lengths, list) or len(lengths) != columns or any(type(n) is not int or not 1 <= n <= 40 for n in lengths):
        return jsonify({"error": "Her sütun için 1 ile 40 arasında hücre sayısı girin."}), 400
    if not isinstance(cell_seats, list) or len(cell_seats) != columns or any(
        not isinstance(col, list) or len(col) != lengths[index]
        or any(type(count) is not int or count not in {1, 2, 3} for count in col)
        for index, col in enumerate(cell_seats)
    ):
        return jsonify({"error": "Her hücre için 1, 2 veya 3 kişilik oturma biçimi seçin."}), 400
    if not isinstance(aisle_after, list) or len(aisle_after) != columns - 1 or any(type(flag) is not bool for flag in aisle_after):
        return jsonify({"error": "Sütunlar arasındaki koridor bilgisi geçersiz."}), 400
    total_seats = sum(sum(col) for col in cell_seats)
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
            return jsonify({"error": "Bu, planın eski bir hâli; güncel planı açıp orada düzenleyin."}), 409
        if session.scalar(select(func.count(Desk.id)).where(Desk.layout_id == layout_id)):
            return jsonify({"error": "Bu planda masalar var. Sıfırdan kurmak için ileri düzey bölümünden yeni bir plan oluşturun."}), 409

        seat_number = 1
        desk_counter = 0
        x_positions = []
        x_cursor = 0.0
        block_number = 1
        for column_index in range(columns):
            x_positions.append((x_cursor, f"B{block_number}"))
            x_cursor += 2.0
            if column_index < columns - 1 and aisle_after[column_index]:
                x_cursor += 2.0
                block_number += 1
        for column_index, (x, block_label) in enumerate(x_positions):
            for row_index, seats_in_cell in enumerate(cell_seats[column_index]):
                desk_counter += 1
                desk = Desk(
                    layout_id=layout_id,
                    label=f"S{row_index + 1}-M{column_index + 1}",
                    block_label=block_label,
                    x=x,
                    y=row_index * 2.0,
                    rotation_degrees=0,
                )
                session.add(desk)
                session.flush()
                for seat_index in range(1, seats_in_cell + 1):
                    session.add(Seat(
                        layout_id=layout_id,
                        desk_id=desk.id,
                        seat_number=seat_number,
                        seat_index=seat_index,
                        x=x + 0.25 + (seat_index - 1) * 0.45,
                        y=row_index * 2.0,
                        is_available=True,
                    ))
                    seat_number += 1
        session.flush()
        response = _layout_payload(session, layout)
    return jsonify({"layout": response, "desk_count": desk_counter, "seat_count": total_seats}), 201
