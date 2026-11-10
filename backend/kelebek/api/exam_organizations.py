"""Sınav organizasyonu taslakları ve ders kataloğu API'si."""

import hashlib
import json
from io import BytesIO

from flask import Blueprint, current_app, jsonify, request, send_file
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from kelebek.db import current_academic_year_start
from kelebek.distribution import progress as distribution_progress
from kelebek.distribution.neighbors import build_neighbor_pairs
from kelebek.distribution.solver import (
    DistributionError,
    evaluate_assignments,
    solve_candidate,
    suggest_violation_fixes,
)
from kelebek.models import (
    AcademicYear,
    Classroom,
    ClassroomLayout,
    Desk,
    DistributionCandidate,
    DistributionEvent,
    DistributionRun,
    ExamOrganization,
    ExamOrganizationClassroom,
    ExamParticipant,
    ExamPeriod,
    Seat,
    SeatAssignment,
)
from kelebek.services.exam_organizer import (
    ExamOrganizerError,
    create_organization,
    list_courses,
    list_organizations,
    list_room_options,
    update_organization_rooms,
    update_organization_rules,
)
from kelebek.services.reporting import (
    ATTENDANCE_REPORT_TYPE,
    CLASS_STUDENT_LIST_REPORT_TYPE,
    CLASS_STUDENT_LIST_XLSX_REPORT_TYPE,
    GENERAL_DISTRIBUTION_REPORT_TYPE,
    GENERAL_DISTRIBUTION_XLSX_REPORT_TYPE,
    ROOM_STUDENT_LIST_REPORT_TYPE,
    ROOM_STUDENT_LIST_XLSX_REPORT_TYPE,
    all_report_statuses,
    build_attendance_pdf,
    build_class_student_list_pdf,
    build_class_student_list_xlsx,
    build_general_distribution_pdf,
    build_general_distribution_xlsx,
    build_room_student_list_pdf,
    build_room_student_list_xlsx,
    build_seating_plan_pdf,
    record_report,
    record_seating_plan_report,
    report_filename,
    report_status,
    resolve_pdf_options,
    resolve_report_fields,
    resolve_report_labels,
    seating_plan_report_filename,
)

exam_organizations_api = Blueprint("exam_organizations", __name__)

RULE_NAMES = (
    "prevent_same_section_adjacent", "prevent_same_section_front_back",
    "prevent_different_grade_same_area_adjacent", "prevent_different_grade_same_area_front_back",
    "prevent_same_grade_area_adjacent", "prevent_same_grade_area_front_back",
)
MANUAL_EVENT_TYPES = {"seat_move", "seat_swap", "seat_to_pool"}


def _candidate_history_state(events):
    undo_stack, redo_stack = [], []
    for event in events:
        if event.event_type in MANUAL_EVENT_TYPES:
            undo_stack.append(event)
            redo_stack.clear()
        elif event.event_type == "undo" and event.related_event_id:
            original = next((item for item in undo_stack if item.id == event.related_event_id), None)
            if original:
                undo_stack.remove(original)
                redo_stack.append(original)
        elif event.event_type == "redo" and event.related_event_id:
            original = next((item for item in redo_stack if item.id == event.related_event_id), None)
            if original:
                redo_stack.remove(original)
                undo_stack.append(original)
    return {"can_undo": bool(undo_stack), "can_redo": bool(redo_stack),
            "undo_count": len(undo_stack), "redo_count": len(redo_stack),
            "undo_event_id": undo_stack[-1].id if undo_stack else None,
            "redo_event_id": redo_stack[-1].id if redo_stack else None}


def _distribution_fingerprint(session, organization):
    participant_rows = session.execute(
        select(ExamParticipant.id, ExamParticipant.class_level, ExamParticipant.section, ExamParticipant.area)
        .where(
            ExamParticipant.organization_id == organization.id,
            ExamParticipant.is_active.is_(True),
        )
        .order_by(ExamParticipant.id)
    ).all()
    layout_ids = session.scalars(
        select(ExamOrganizationClassroom.layout_id)
        .where(ExamOrganizationClassroom.organization_id == organization.id)
        .order_by(ExamOrganizationClassroom.layout_id)
    ).all()
    physical_layouts = []
    for layout_id in layout_ids:
        desks = session.execute(
            select(Desk.id, Desk.x, Desk.y, Desk.block_label)
            .where(Desk.layout_id == layout_id).order_by(Desk.id)
        ).all()
        seats = session.execute(
            select(Seat.id, Seat.desk_id, Seat.seat_index, Seat.is_available)
            .where(Seat.layout_id == layout_id).order_by(Seat.id)
        ).all()
        physical_layouts.append({"desks": [list(row) for row in desks], "seats": [list(row) for row in seats]})
    snapshot = {
        "participants": [list(row) for row in participant_rows],
        "layouts": layout_ids,
        "physical_layouts": physical_layouts,
        "rules": [bool(getattr(organization, name)) for name in RULE_NAMES],
    }
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _candidate_summary(assignments, room_capacities):
    groups = {}
    used_by_room = {}
    for assignment in assignments:
        key = (assignment["class_level"], assignment["section"], assignment.get("area") or "")
        group = groups.setdefault(key, {"class_level": key[0], "section": key[1], "area": key[2] or None, "student_count": 0})
        group["student_count"] += 1
        if assignment.get("classroom_id"):
            used_by_room[assignment["classroom_id"]] = used_by_room.get(assignment["classroom_id"], 0) + 1
    rooms = [{
        "classroom_id": room_id,
        "classroom_name": room["name"],
        "available_seats": room["available_seats"],
        "assigned_students": used_by_room.get(room_id, 0),
        "empty_seats": room["available_seats"] - used_by_room.get(room_id, 0),
    } for room_id, room in room_capacities.items()]
    return {"groups": list(groups.values()), "rooms": rooms, "waiting_count": sum(not item.get("seat_id") for item in assignments)}


SOLVER_TIME_LIMIT_SECONDS = 12.0


def _review_selected_candidate(session, organization, candidate_id=None):
    candidate_id = candidate_id or organization.selected_candidate_id
    if not candidate_id:
        raise ValueError("Önce incelenecek dağıtım adayını seçin.")
    candidate = session.get(DistributionCandidate, candidate_id)
    run = session.get(DistributionRun, candidate.run_id) if candidate else None
    if candidate is None or run is None or run.organization_id != organization.id or run.config_hash != _distribution_fingerprint(session, organization):
        raise ValueError("Seçili aday güncel değil. Güncel derslik ve kurallarla yeni aday üretin.")
    participants = session.scalars(select(ExamParticipant).where(
        ExamParticipant.organization_id == organization.id,
        ExamParticipant.is_active.is_(True),
    )).all()
    selections = session.execute(
        select(ExamOrganizationClassroom, Classroom, ClassroomLayout)
        .join(Classroom, Classroom.id == ExamOrganizationClassroom.classroom_id)
        .join(ClassroomLayout, ClassroomLayout.id == ExamOrganizationClassroom.layout_id)
        .where(ExamOrganizationClassroom.organization_id == organization.id)
    ).all()
    seat_pairs = {"adjacent": [], "front_back": []}
    available_seat_ids = set()
    room_capacities = []
    seat_info = {}
    for _selection, _classroom, layout in selections:
        desks = session.scalars(select(Desk).where(Desk.layout_id == layout.id)).all()
        desk_positions = {desk.id: (desk.x, desk.y) for desk in desks}
        seats_by_desk = {}
        seats = session.scalars(select(Seat).where(Seat.layout_id == layout.id)).all()
        for seat in seats:
            seats_by_desk.setdefault(seat.desk_id, []).append(seat)
            if seat.is_available:
                available_seat_ids.add(seat.id)
                x, y = desk_positions.get(seat.desk_id, (0.0, 0.0))
                seat_info[seat.id] = {"classroom_id": _classroom.id, "classroom_name": _classroom.name,
                                      "seat_number": seat.seat_number, "x": x + seat.seat_index * 0.3, "y": y}
        graph = build_neighbor_pairs([{
            "id": desk.id, "x": desk.x, "y": desk.y, "block_label": desk.block_label,
            "seats": [{"id": seat.id, "seat_index": seat.seat_index, "is_available": seat.is_available} for seat in seats_by_desk.get(desk.id, [])],
        } for desk in desks])
        seat_pairs["adjacent"].extend(graph["adjacent"])
        seat_pairs["front_back"].extend(graph["front_back"])
        room_capacities.append({"classroom_id": _classroom.id, "classroom_name": _classroom.name, "available_seats": len([seat for seat in seats if seat.is_available])})
    rows = session.scalars(
        select(SeatAssignment)
        .join(ExamParticipant, ExamParticipant.id == SeatAssignment.participant_id)
        .where(
            SeatAssignment.candidate_id == candidate.id,
            ExamParticipant.is_active.is_(True),
        )
    ).all()
    assignment_map = {row.participant_id: row.seat_id for row in rows}
    if len(rows) != len(participants) or len(assignment_map) != len(participants):
        raise ValueError("Adayda her öğrenci için tam olarak bir koltuk bulunmalı.")
    seated_seat_ids = {seat_id for seat_id in assignment_map.values() if seat_id is not None}
    if any(seat_id not in available_seat_ids for seat_id in seated_seat_ids):
        raise ValueError("Adayda seçili olmayan veya kullanım dışı bir koltuk var. Yeniden dağıtım yapın.")
    rules = {name: getattr(organization, name) for name in RULE_NAMES}
    seated_assignments = {participant_id: seat_id for participant_id, seat_id in assignment_map.items() if seat_id is not None}
    participant_payloads = [{
        "id": item.id, "class_level": item.class_level, "section": item.section, "area": item.area,
    } for item in participants]
    evaluation = evaluate_assignments(participant_payloads, seat_pairs, rules, seated_assignments)
    evaluation["suggestions"] = suggest_violation_fixes(
        participant_payloads, seat_pairs, rules, seated_assignments, seat_info, evaluation["violations"])
    assigned_by_room = {}
    seat_room = {seat.id: classroom.id for selection, classroom, layout in selections
                 for seat in session.scalars(select(Seat).where(Seat.layout_id == layout.id)).all()}
    for seat_id in seated_seat_ids:
        room_id = seat_room.get(seat_id)
        assigned_by_room[room_id] = assigned_by_room.get(room_id, 0) + 1
    return {
        "candidate_id": candidate.id,
        "participant_count": len(participants),
        "unassigned_count": len(participants) - len(seated_assignments),
        "seated_count": len(seated_assignments),
        "available_capacity": len(available_seat_ids),
        "empty_seats": len(available_seat_ids) - len(seated_assignments),
        **evaluation,
        "rooms": [{**room, "assigned_students": assigned_by_room.get(room["classroom_id"], 0),
                   "empty_seats": room["available_seats"] - assigned_by_room.get(room["classroom_id"], 0)} for room in room_capacities],
        "can_finalize": len(seated_assignments) == len(participants) and evaluation["affected_student_count"] <= 5,
    }


def _serialize_candidate(session, organization, candidate):
    rows = session.execute(
        select(SeatAssignment, ExamParticipant, Seat, Classroom)
        .join(ExamParticipant, ExamParticipant.id == SeatAssignment.participant_id)
        .outerjoin(Seat, Seat.id == SeatAssignment.seat_id)
        .outerjoin(Desk, Desk.id == Seat.desk_id)
        .outerjoin(ClassroomLayout, ClassroomLayout.id == Desk.layout_id)
        .outerjoin(Classroom, Classroom.id == ClassroomLayout.classroom_id)
        .where(SeatAssignment.candidate_id == candidate.id)
        .where(ExamParticipant.is_active.is_(True))
        .order_by(Classroom.name, Seat.seat_number)
    ).all()
    assignments = [{
        "participant_id": assignment.participant_id, "seat_id": seat.id if seat else None,
        "seat_number": seat.seat_number if seat else None, "classroom_id": classroom.id if classroom else None,
        "classroom_name": classroom.name if classroom else None, "first_name": participant.first_name,
        "last_name": participant.last_name, "school_number": participant.school_number,
        "class_level": participant.class_level, "section": participant.section,
        "area": participant.area,
    } for assignment, participant, seat, classroom in rows]
    room_rows = session.execute(
        select(Classroom.id, Classroom.name, Seat.id, Seat.seat_number)
        .join(ExamOrganizationClassroom, ExamOrganizationClassroom.classroom_id == Classroom.id)
        .join(ClassroomLayout, ClassroomLayout.id == ExamOrganizationClassroom.layout_id)
        .join(Seat, Seat.layout_id == ClassroomLayout.id)
        .where(ExamOrganizationClassroom.organization_id == organization.id, Seat.is_available.is_(True))
        .order_by(Classroom.name, Seat.seat_number)
    ).all()
    capacities = {}
    available_seats = []
    for room_id, room_name, seat_id, seat_number in room_rows:
        capacities.setdefault(room_id, {"name": room_name, "available_seats": 0})["available_seats"] += 1
        available_seats.append({"seat_id": seat_id, "seat_number": seat_number, "classroom_id": room_id, "classroom_name": room_name})
    assignment_by_seat = {item["seat_id"]: item for item in assignments if item["seat_id"]}
    plan = []
    selections = session.execute(
        select(ExamOrganizationClassroom, Classroom, ClassroomLayout)
        .join(Classroom, Classroom.id == ExamOrganizationClassroom.classroom_id)
        .join(ClassroomLayout, ClassroomLayout.id == ExamOrganizationClassroom.layout_id)
        .where(ExamOrganizationClassroom.organization_id == organization.id)
        .order_by(Classroom.name)
    ).all()
    for _selection, classroom, layout in selections:
        desks = session.scalars(
            select(Desk).where(Desk.layout_id == layout.id).order_by(Desk.y, Desk.x)
        ).all()
        desk_payloads = []
        for desk in desks:
            seats = session.scalars(
                select(Seat).where(Seat.desk_id == desk.id).order_by(Seat.seat_index)
            ).all()
            desk_payloads.append({
                "desk_id": desk.id, "label": desk.label, "block_label": desk.block_label,
                "x": desk.x, "y": desk.y,
                "seats": [{
                    "seat_id": seat.id, "seat_number": seat.seat_number,
                    "seat_index": seat.seat_index, "x": seat.x, "y": seat.y,
                    "is_available": seat.is_available,
                    "student": assignment_by_seat.get(seat.id),
                } for seat in seats],
            })
        plan.append({
            "classroom_id": classroom.id, "classroom_name": classroom.name,
            "layout_id": layout.id, "layout_name": layout.name, "desks": desk_payloads,
        })
    event_rows = session.execute(
        select(DistributionEvent, ExamParticipant)
        .join(ExamParticipant, ExamParticipant.id == DistributionEvent.participant_id)
        .where(DistributionEvent.candidate_id == candidate.id)
        .order_by(DistributionEvent.created_at, DistributionEvent.id)
    ).all()
    return {
        "candidate_id": candidate.id,
        "run_id": candidate.run_id,
        "generation_index": candidate.generation_index,
        "derived_from_candidate_id": candidate.derived_from_candidate_id,
        "pinned_classroom_ids": json.loads(candidate.pinned_classroom_ids) if candidate.pinned_classroom_ids else [],
        "status": candidate.status,
        "affected_student_count": candidate.affected_student_count,
        "events": [{
            "id": event.id,
            "event_type": event.event_type,
            "participant_id": event.participant_id,
            "participant_name": f"{participant.first_name} {participant.last_name}",
            "school_number": participant.school_number,
            "displaced_participant_id": event.displaced_participant_id,
            "from_seat_id": event.from_seat_id,
            "to_seat_id": event.to_seat_id,
            "related_event_id": event.related_event_id,
            "created_at": event.created_at.isoformat(),
        } for event, participant in event_rows],
        "history": _candidate_history_state([event for event, _participant in event_rows]),
        "summary": _candidate_summary(assignments, capacities),
        "available_seats": available_seats,
        "assignments": assignments,
        "plan": plan,
        "violations": (violation_review := _candidate_violations(session, organization, candidate))["violations"],
        "violation_suggestions": violation_review["suggestions"],
    }


def _candidate_violations(session, organization, candidate):
    empty = {"violations": [], "suggestions": {}}
    run = session.get(DistributionRun, candidate.run_id)
    if run is None or run.config_hash != _distribution_fingerprint(session, organization):
        return empty
    try:
        review = _review_selected_candidate(session, organization, candidate.id)
    except ValueError:
        return empty
    return {"violations": review["violations"], "suggestions": review["suggestions"]}


@exam_organizations_api.get("/courses")
def get_courses():
    session_factory = current_app.extensions["kelebek_session_factory"]
    with session_factory() as session:
        courses = list_courses(session)
    return jsonify({"courses": courses})


@exam_organizations_api.get("/exam-room-options")
def get_exam_room_options():
    academic_year_id = request.args.get("academic_year_id", "").strip()
    if not academic_year_id:
        return jsonify({"error": "Eğitim-öğretim yılı gerekli."}), 400
    session_factory = current_app.extensions["kelebek_session_factory"]
    with session_factory() as session:
        if session.get(AcademicYear, academic_year_id) is None:
            return jsonify({"error": "Seçili eğitim-öğretim yılı bulunamadı."}), 404
        rooms = list_room_options(session, academic_year_id)
    return jsonify({"rooms": rooms})


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


@exam_organizations_api.patch("/exam-organizations/<organization_id>/period")
def patch_exam_organization_period(organization_id: str):
    """Sınavı başka bir döneme taşı (0018 öncesi dönemsiz kayıtlar için de gerekir)."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Dönem bilgisi JSON biçiminde gönderilmelidir."}), 400
    period_id = payload.get("exam_period_id")
    if not isinstance(period_id, str) or not period_id.strip():
        return jsonify({"error": "Sınav dönemi seçin."}), 400

    session_factory = current_app.extensions["kelebek_session_factory"]
    with session_factory.begin() as session:
        organization = session.get(ExamOrganization, organization_id)
        if organization is None:
            return jsonify({"error": "Sınav organizasyonu bulunamadı."}), 404
        if organization.archived_at is not None:
            return jsonify({"error": "Arşivlenmiş sınav salt okunur."}), 403
        period = session.get(ExamPeriod, period_id.strip())
        if period is None:
            return jsonify({"error": "Dönem bulunamadı."}), 404
        if period.academic_year_id != organization.academic_year_id:
            return jsonify({"error": "Seçilen dönem bu eğitim-öğretim yılına ait değil."}), 400
        organization.exam_period_id = period.id
        result = {"id": organization.id, "exam_period_id": period.id, "exam_period_name": period.name}
    return jsonify({"organization": result})


@exam_organizations_api.put("/exam-organizations/<organization_id>/classrooms")
def put_exam_organization_classrooms(organization_id: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Derslik seçimleri JSON biçiminde gönderilmelidir."}), 400
    session_factory = current_app.extensions["kelebek_session_factory"]
    try:
        with session_factory.begin() as session:
            organization = update_organization_rooms(session, organization_id, payload)
    except ExamOrganizerError as error:
        return jsonify({"error": str(error)}), error.status_code
    except IntegrityError:
        return jsonify({"error": "Derslik seçimi aynı anda değişti; sayfayı yenileyip tekrar deneyin."}), 409
    return jsonify({"organization": organization})


@exam_organizations_api.put("/exam-organizations/<organization_id>/rules")
def put_exam_organization_rules(organization_id: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Dağıtım kuralları JSON biçiminde gönderilmelidir."}), 400
    session_factory = current_app.extensions["kelebek_session_factory"]
    try:
        with session_factory.begin() as session:
            organization = update_organization_rules(session, organization_id, payload)
    except ExamOrganizerError as error:
        return jsonify({"error": str(error)}), error.status_code
    except IntegrityError:
        return jsonify({"error": "Kurallar aynı anda değişti; sayfayı yenileyip tekrar deneyin."}), 409
    return jsonify({"organization": organization})


@exam_organizations_api.post("/exam-organizations/<organization_id>/distribution-candidates")
def create_distribution_candidate(organization_id: str):
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "Aday bilgileri geçersiz."}), 400
    requested_run_id = payload.get("run_id")
    base_candidate_id = payload.get("base_candidate_id")
    pinned_classroom_ids = payload.get("pinned_classroom_ids") or []
    if not isinstance(pinned_classroom_ids, list) or any(not isinstance(item, str) for item in pinned_classroom_ids):
        return jsonify({"error": "Sabitlenecek derslik seçimi geçersiz."}), 400
    if pinned_classroom_ids and (not isinstance(base_candidate_id, str) or not requested_run_id):
        return jsonify({"error": "Derslik sabitlemek için önce mevcut bir adayı seçin."}), 400
    session_factory = current_app.extensions["kelebek_session_factory"]
    existing = distribution_progress.get(organization_id)
    if existing and not existing.finished:
        return jsonify({"error": "Bu sınav için dağıtım zaten hesaplanıyor."}), 409
    progress = distribution_progress.start(organization_id, SOLVER_TIME_LIMIT_SECONDS)
    outcome = "error"
    try:
        with session_factory.begin() as session:
            organization = session.get(ExamOrganization, organization_id)
            if organization is None:
                return jsonify({"error": "Sınav organizasyonu bulunamadı."}), 404
            year = session.get(AcademicYear, organization.academic_year_id)
            if year is None or year.start_year < current_academic_year_start() or organization.status != "draft":
                return jsonify({"error": "Bu organizasyonda dağıtım adayı oluşturulamaz."}), 403
            participants = session.scalars(
                select(ExamParticipant).where(
                    ExamParticipant.organization_id == organization.id,
                    ExamParticipant.is_active.is_(True),
                )
                .order_by(ExamParticipant.class_level, ExamParticipant.section, ExamParticipant.school_number)
            ).all()
            selections = session.execute(
                select(ExamOrganizationClassroom, Classroom, ClassroomLayout)
                .join(Classroom, Classroom.id == ExamOrganizationClassroom.classroom_id)
                .join(ClassroomLayout, ClassroomLayout.id == ExamOrganizationClassroom.layout_id)
                .where(ExamOrganizationClassroom.organization_id == organization.id)
            ).all()
            if not selections:
                return jsonify({"error": "Dağıtımdan önce en az bir derslik seçin."}), 409
            rooms, all_pairs = [], {"adjacent": [], "front_back": []}
            seat_labels = {}
            for _selection, classroom, layout in selections:
                desks = session.scalars(select(Desk).where(Desk.layout_id == layout.id)).all()
                seats_by_desk = {}
                for seat in session.scalars(select(Seat).where(Seat.layout_id == layout.id)).all():
                    seats_by_desk.setdefault(seat.desk_id, []).append(seat)
                    seat_labels[seat.id] = {"seat_number": seat.seat_number, "classroom_id": classroom.id, "classroom_name": classroom.name}
                graph = build_neighbor_pairs([{
                    "id": desk.id, "x": desk.x, "y": desk.y, "block_label": desk.block_label,
                    "seats": [{"id": seat.id, "seat_index": seat.seat_index, "is_available": seat.is_available} for seat in seats_by_desk.get(desk.id, [])],
                } for desk in desks])
                all_pairs["adjacent"].extend(graph["adjacent"])
                all_pairs["front_back"].extend(graph["front_back"])
                rooms.append({"id": classroom.id, "seats": [
                    {"id": seat.id, "classroom_id": classroom.id, "is_available": seat.is_available}
                    for desk_seats in seats_by_desk.values() for seat in desk_seats
                ]})
            rules = {name: getattr(organization, name) for name in (
                "prevent_same_section_adjacent", "prevent_same_section_front_back",
                "prevent_different_grade_same_area_adjacent", "prevent_different_grade_same_area_front_back",
                "prevent_same_grade_area_adjacent", "prevent_same_grade_area_front_back",
            )}
            config_hash = _distribution_fingerprint(session, organization)
            previous_assignments = []
            if requested_run_id:
                run = session.get(DistributionRun, requested_run_id)
                if run is None or run.organization_id != organization.id or run.config_hash != config_hash:
                    return jsonify({"error": "Sınav, derslikler veya kurallar değişti. Yeni bir dağıtım çalışması başlatın."}), 409
                previous_candidates = session.scalars(
                    select(DistributionCandidate).where(DistributionCandidate.run_id == run.id)
                    .order_by(DistributionCandidate.generation_index)
                ).all()
                for previous_candidate in previous_candidates:
                    previous_assignments.append([{
                        "participant_id": row.participant_id, "seat_id": row.seat_id,
                    } for row in session.scalars(
                        select(SeatAssignment).where(SeatAssignment.candidate_id == previous_candidate.id)
                    ).all()])
                generation_index = (max((item.generation_index for item in previous_candidates), default=0)) + 1
            else:
                run = DistributionRun(organization_id=organization.id, status="completed", config_hash=config_hash)
                session.add(run)
                session.flush()
                generation_index = 1
            fixed_assignments = {}
            if pinned_classroom_ids:
                base = session.get(DistributionCandidate, base_candidate_id)
                if base is None or base.run_id != run.id:
                    return jsonify({"error": "Sabitleme için seçilen aday bu dağıtım çalışmasına ait değil."}), 409
                selected_room_ids = {room["id"] for room in rooms}
                if set(pinned_classroom_ids) - selected_room_ids:
                    return jsonify({"error": "Sabitlenecek derslik bu sınavda seçili değil."}), 409
                if set(pinned_classroom_ids) == selected_room_ids:
                    return jsonify({"error": "Tüm derslikler sabitlenemez; en az bir dersliği yeniden dağıtıma bırakın."}), 409
                active_ids = {item.id for item in participants}
                for row in session.scalars(select(SeatAssignment).where(SeatAssignment.candidate_id == base.id)).all():
                    if row.seat_id and row.participant_id in active_ids and seat_labels.get(row.seat_id, {}).get("classroom_id") in pinned_classroom_ids:
                        fixed_assignments[row.participant_id] = row.seat_id
                fixed_seats = set(fixed_assignments.values())
                for room in rooms:
                    if room["id"] in pinned_classroom_ids:
                        room["seats"] = [{**seat, "is_available": seat["is_available"] and seat["id"] in fixed_seats} for seat in room["seats"]]
                        if not room["seats"] or not any(seat["is_available"] for seat in room["seats"]):
                            rooms = [item for item in rooms if item["id"] != room["id"]]
            progress.set_stage("model")
            result = solve_candidate([{
                "id": item.id, "class_level": item.class_level, "section": item.section,
                "area": item.area, "first_name": item.first_name,
                "last_name": item.last_name, "school_number": item.school_number,
            } for item in participants], rooms, all_pairs, rules, previous_assignments=previous_assignments,
               fixed_assignments=fixed_assignments, time_limit=SOLVER_TIME_LIMIT_SECONDS, progress=progress)
            progress.set_stage("save")
            stopped_early = result["stopped"]
            candidate = DistributionCandidate(
                run_id=run.id, status="stopped" if stopped_early else result["status"],
                affected_student_count=result["affected_student_count"],
                objective_value=result["objective"],
                generation_index=generation_index,
                derived_from_candidate_id=base_candidate_id if pinned_classroom_ids else None,
                pinned_classroom_ids=json.dumps(sorted(pinned_classroom_ids)) if pinned_classroom_ids else None,
            )
            session.add(candidate)
            session.flush()
            for assignment in result["assignments"]:
                session.add(SeatAssignment(
                    candidate_id=candidate.id,
                    participant_id=assignment["participant_id"],
                    seat_id=assignment["seat_id"],
                ))
            result = _serialize_candidate(session, organization, candidate)
            result["objective"] = candidate.objective_value
            result["stopped_early"] = stopped_early
        outcome = "stopped" if stopped_early else "created"
    except DistributionError as error:
        return jsonify({"error": str(error)}), 409
    except IntegrityError:
        return jsonify({"error": "Aday kaydedilemedi; veriler değişmiş olabilir. Yenileyip tekrar deneyin."}), 409
    finally:
        distribution_progress.finish(progress, outcome)
    return jsonify({"candidate": result}), 201


@exam_organizations_api.get("/exam-organizations/<organization_id>/distribution-progress")
def get_distribution_progress(organization_id: str):
    progress = distribution_progress.get(organization_id)
    return jsonify({"progress": progress.snapshot() if progress else None})


@exam_organizations_api.post("/exam-organizations/<organization_id>/distribution-progress/stop")
def stop_distribution_progress(organization_id: str):
    progress = distribution_progress.get(organization_id)
    if progress is None or progress.finished:
        return jsonify({"error": "Çalışan bir dağıtım yok."}), 409
    progress.stop_event.set()
    return jsonify({"progress": progress.snapshot()})


@exam_organizations_api.get("/exam-organizations/<organization_id>/distribution-candidates")
def list_distribution_candidates(organization_id: str):
    session_factory = current_app.extensions["kelebek_session_factory"]
    with session_factory() as session:
        organization = session.get(ExamOrganization, organization_id)
        if organization is None:
            return jsonify({"error": "Sınav organizasyonu bulunamadı."}), 404
        fingerprint = _distribution_fingerprint(session, organization)
        run = session.scalar(
            select(DistributionRun).where(
                DistributionRun.organization_id == organization.id,
                DistributionRun.config_hash == fingerprint,
            ).order_by(DistributionRun.created_at.desc())
        )
        if run is None:
            return jsonify({"candidates": []})
        candidates = session.scalars(
            select(DistributionCandidate).where(DistributionCandidate.run_id == run.id)
            .order_by(DistributionCandidate.generation_index)
        ).all()
        result = []
        for candidate in candidates:
            result.append(_serialize_candidate(session, organization, candidate))
    return jsonify({"candidates": result})


@exam_organizations_api.put("/exam-organizations/<organization_id>/selected-candidate")
def select_distribution_candidate(organization_id: str):
    payload = request.get_json(silent=True)
    candidate_id = payload.get("candidate_id") if isinstance(payload, dict) else None
    if not isinstance(candidate_id, str) or not candidate_id:
        return jsonify({"error": "İncelenecek dağıtım adayı seçilmelidir."}), 400
    session_factory = current_app.extensions["kelebek_session_factory"]
    try:
        with session_factory.begin() as session:
            organization = session.get(ExamOrganization, organization_id)
            candidate = session.get(DistributionCandidate, candidate_id)
            if organization is None or candidate is None:
                return jsonify({"error": "Sınav veya aday bulunamadı."}), 404
            run = session.get(DistributionRun, candidate.run_id)
            if run is None or run.organization_id != organization.id or run.config_hash != _distribution_fingerprint(session, organization):
                return jsonify({"error": "Bu adayın derslikleri, kuralları veya katılımcıları güncel değil; yeniden dağıtım yapın."}), 409
            year = session.get(AcademicYear, organization.academic_year_id)
            if year is None or year.start_year < current_academic_year_start() or organization.status != "draft":
                return jsonify({"error": "Arşiv veya kesinleşmiş organizasyonda aday seçilemez."}), 403
            assignment_count = session.scalar(
                select(func.count(SeatAssignment.id)).where(SeatAssignment.candidate_id == candidate.id)
            ) or 0
            participant_count = session.scalar(
                select(func.count(ExamParticipant.id)).where(
                    ExamParticipant.organization_id == organization.id,
                    ExamParticipant.is_active.is_(True),
                )
            ) or 0
            if assignment_count != participant_count or candidate.affected_student_count > 5:
                return jsonify({"error": "Bu aday son kontrole alınamaz; tüm öğrenciler yerleşmeli ve en fazla beş öğrenci kural ihlalinden etkilenmelidir."}), 409
            organization.selected_candidate_id = candidate.id
    except IntegrityError:
        return jsonify({"error": "Aday seçimi kaydedilemedi; sayfayı yenileyip tekrar deneyin."}), 409
    return jsonify({"selected_candidate_id": candidate_id})


def _set_assignment_pair(session, assignments, participant_id, moving_target_id, displaced_id=None,
                         displaced_target_id=None):
    by_participant = {item.participant_id: item for item in assignments}
    moving = by_participant.get(participant_id)
    displaced = by_participant.get(displaced_id) if displaced_id else None
    if moving is None or (displaced_id and displaced is None):
        raise ValueError("İşlem geçmişindeki öğrenci artık bu dağıtımda bulunmuyor.")
    moving.seat_id = None
    session.flush()
    if displaced:
        displaced.seat_id = displaced_target_id
        session.flush()
    moving.seat_id = moving_target_id
    session.flush()
    return moving, displaced


@exam_organizations_api.post("/exam-organizations/<organization_id>/distribution-candidates/<candidate_id>/moves")
def move_candidate_participant(organization_id: str, candidate_id: str):
    payload = request.get_json(silent=True)
    participant_id = payload.get("participant_id") if isinstance(payload, dict) else None
    target_seat_id = payload.get("target_seat_id") if isinstance(payload, dict) else None
    if not isinstance(participant_id, str) or (target_seat_id is not None and not isinstance(target_seat_id, str)):
        return jsonify({"error": "Öğrenci veya hedef koltuk bilgisi geçersiz."}), 400
    session_factory = current_app.extensions["kelebek_session_factory"]
    try:
        with session_factory.begin() as session:
            organization = session.get(ExamOrganization, organization_id)
            candidate = session.get(DistributionCandidate, candidate_id)
            if organization is None or candidate is None:
                return jsonify({"error": "Sınav veya aday bulunamadı."}), 404
            if organization.status not in {"draft", "completed"} or organization.selected_candidate_id != candidate.id:
                return jsonify({"error": "Önce bu adayı incelemeye alın."}), 409
            year = session.get(AcademicYear, organization.academic_year_id)
            run = session.get(DistributionRun, candidate.run_id)
            if year is None:
                return jsonify({"error": "Eğitim-öğretim yılı bulunamadı."}), 404
            if year.start_year < current_academic_year_start():
                return jsonify({"error": "Arşiv yılındaki kesinleşmiş dağıtım salt okunurdur."}), 403
            if run is None or run.config_hash != _distribution_fingerprint(session, organization):
                return jsonify({"error": "Adayın verileri güncel değil; yeni aday üretin."}), 409
            try:
                _review_selected_candidate(session, organization)
            except ValueError as error:
                return jsonify({"error": str(error)}), 409
            assignments = session.scalars(select(SeatAssignment).where(SeatAssignment.candidate_id == candidate.id)).all()
            by_participant = {item.participant_id: item for item in assignments}
            moving = by_participant.get(participant_id)
            target = session.get(Seat, target_seat_id) if target_seat_id else None
            selected_layout_ids = set(session.scalars(select(ExamOrganizationClassroom.layout_id).where(ExamOrganizationClassroom.organization_id == organization.id)).all())
            if moving is None:
                return jsonify({"error": "Öğrenci bu adayda bulunamadı."}), 409
            if target_seat_id and (target is None or target.layout_id not in selected_layout_ids or not target.is_available):
                return jsonify({"error": "Öğrenci veya hedef kullanılabilir koltuk bulunamadı."}), 409
            if target and moving.seat_id == target.id:
                return jsonify({"error": "Öğrenci zaten bu koltukta."}), 400
            if target is None and moving.seat_id is None:
                return jsonify({"error": "Öğrenci zaten bekleyen havuzda."}), 400
            target_assignment = next((item for item in assignments if target and item.seat_id == target.id), None)
            displaced_id = target_assignment.participant_id if target_assignment else None
            source_seat_id = moving.seat_id
            event_type = "seat_to_pool" if target is None else "seat_swap" if target_assignment else "seat_move"
            if organization.status == "completed":
                _set_assignment_pair(
                    session, assignments, participant_id, target.id if target else None,
                    displaced_id, source_seat_id if target_assignment else None,
                )
                candidate.status = "manual"
                session.add(DistributionEvent(
                    candidate_id=candidate.id,
                    event_type=event_type,
                    participant_id=participant_id,
                    displaced_participant_id=displaced_id,
                    from_seat_id=source_seat_id,
                    to_seat_id=target.id if target else None,
                ))
                session.flush()
                review = _review_selected_candidate(session, organization)
                candidate.affected_student_count = review["affected_student_count"]
                result = _serialize_candidate(session, organization, candidate)
                result["report_status"] = report_status(session, organization)["report_status"]
                result["report_statuses"] = all_report_statuses(session, organization)
            else:
                child = DistributionCandidate(
                    run_id=run.id,
                    derived_from_candidate_id=candidate.id,
                    status="manual",
                    affected_student_count=0,
                    objective_value=candidate.objective_value,
                    generation_index=(session.scalar(select(func.max(DistributionCandidate.generation_index)).where(DistributionCandidate.run_id == run.id)) or 0) + 1,
                )
                session.add(child)
                session.flush()
                for item in assignments:
                    seat_id = item.seat_id
                    if item.participant_id == participant_id:
                        seat_id = target.id if target else None
                    elif target_assignment and item.participant_id == displaced_id:
                        seat_id = source_seat_id
                    session.add(SeatAssignment(candidate_id=child.id, participant_id=item.participant_id, seat_id=seat_id))
                session.add(DistributionEvent(
                    candidate_id=child.id,
                    event_type=event_type,
                    participant_id=participant_id,
                    displaced_participant_id=displaced_id,
                    from_seat_id=source_seat_id,
                    to_seat_id=target.id if target else None,
                ))
                session.flush()
                review = _review_selected_candidate(session, organization, candidate_id=child.id)
                child.affected_student_count = review["affected_student_count"]
                organization.selected_candidate_id = child.id
                session.flush()
                result = _serialize_candidate(session, organization, child)
            result["review"] = review
    except IntegrityError:
        return jsonify({"error": "Taşıma kaydedilemedi; koltuk durumu değişmiş olabilir."}), 409
    return jsonify({"candidate": result}), 201


@exam_organizations_api.post("/exam-organizations/<organization_id>/distribution-candidates/<candidate_id>/fix-violations")
def fix_candidate_violations(organization_id: str, candidate_id: str):
    """Önerileri sırayla uygula: her adımda ihlalli bir öğrenciyi ihlalsiz boş yere taşı."""
    session_factory = current_app.extensions["kelebek_session_factory"]
    try:
        with session_factory.begin() as session:
            organization = session.get(ExamOrganization, organization_id)
            candidate = session.get(DistributionCandidate, candidate_id)
            if organization is None or candidate is None:
                return jsonify({"error": "Sınav veya aday bulunamadı."}), 404
            if organization.status not in {"draft", "completed"} or organization.selected_candidate_id != candidate.id:
                return jsonify({"error": "Önce bu adayı incelemeye alın."}), 409
            year = session.get(AcademicYear, organization.academic_year_id)
            if year is None or year.start_year < current_academic_year_start():
                return jsonify({"error": "Arşiv yılındaki kesinleşmiş dağıtım salt okunurdur."}), 403
            run = session.get(DistributionRun, candidate.run_id)
            if run is None or run.config_hash != _distribution_fingerprint(session, organization):
                return jsonify({"error": "Adayın verileri güncel değil; yeni aday üretin."}), 409
            review = _review_selected_candidate(session, organization)
            if not review["violations"]:
                return jsonify({"error": "Bu adayda düzeltilecek komşuluk ihlali yok."}), 409
            before = review["affected_student_count"]
            target = candidate
            if organization.status == "draft":
                target = DistributionCandidate(
                    run_id=run.id, derived_from_candidate_id=candidate.id, status="manual",
                    affected_student_count=before, objective_value=candidate.objective_value,
                    generation_index=(session.scalar(select(func.max(DistributionCandidate.generation_index)).where(DistributionCandidate.run_id == run.id)) or 0) + 1,
                )
                session.add(target)
                session.flush()
                for item in session.scalars(select(SeatAssignment).where(SeatAssignment.candidate_id == candidate.id)).all():
                    session.add(SeatAssignment(candidate_id=target.id, participant_id=item.participant_id, seat_id=item.seat_id))
                organization.selected_candidate_id = target.id
                session.flush()
            moved = 0
            for _attempt in range(len(review["suggestions"]) * 2 + 2):
                if not review["violations"]:
                    break
                counts = {}
                for item in review["violations"]:
                    for key in ("first_participant_id", "second_participant_id"):
                        counts[item[key]] = counts.get(item[key], 0) + 1
                choice = next((pid for pid in sorted(counts, key=lambda pid: -counts[pid]) if review["suggestions"].get(pid)), None)
                if choice is None:
                    break
                seat_id = review["suggestions"][choice][0]["seat_id"]
                assignment = session.scalar(select(SeatAssignment).where(
                    SeatAssignment.candidate_id == target.id, SeatAssignment.participant_id == choice))
                session.add(DistributionEvent(candidate_id=target.id, event_type="seat_move", participant_id=choice,
                                              from_seat_id=assignment.seat_id, to_seat_id=seat_id))
                assignment.seat_id = seat_id
                session.flush()
                moved += 1
                review = _review_selected_candidate(session, organization)
            if not moved:
                raise ValueError("İhlalli öğrenciler için ihlalsiz boş yer bulunamadı; yer değiştirmeyi krokiden yapın.")
            target.status = "manual"
            target.affected_student_count = review["affected_student_count"]
            session.flush()
            result = _serialize_candidate(session, organization, target)
            result["review"] = review
            result["fix_summary"] = {"moved": moved, "affected_before": before, "affected_after": review["affected_student_count"]}
            if organization.status == "completed":
                result["report_status"] = report_status(session, organization)["report_status"]
                result["report_statuses"] = all_report_statuses(session, organization)
    except ValueError as error:
        return jsonify({"error": str(error)}), 409
    except IntegrityError:
        return jsonify({"error": "Düzeltme kaydedilemedi; koltuk durumu değişmiş olabilir."}), 409
    return jsonify({"candidate": result}), 201


@exam_organizations_api.post("/exam-organizations/<organization_id>/distribution-candidates/<candidate_id>/history/<action>")
def change_completed_distribution_history(organization_id: str, candidate_id: str, action: str):
    if action not in {"undo", "redo"}:
        return jsonify({"error": "Geçmiş işlemi geçersiz."}), 404
    session_factory = current_app.extensions["kelebek_session_factory"]
    try:
        with session_factory.begin() as session:
            organization = session.get(ExamOrganization, organization_id)
            candidate = session.get(DistributionCandidate, candidate_id)
            if organization is None or candidate is None:
                return jsonify({"error": "Sınav veya dağıtım bulunamadı."}), 404
            run = session.get(DistributionRun, candidate.run_id)
            if run is None or run.organization_id != organization.id:
                return jsonify({"error": "Sınav veya dağıtım bulunamadı."}), 404
            if organization.status != "completed" or organization.selected_candidate_id != candidate.id:
                return jsonify({"error": "İşlem geçmişi yalnızca seçili, kesinleşmiş dağıtımda değiştirilebilir."}), 409
            year = session.get(AcademicYear, organization.academic_year_id)
            if year is None or year.start_year < current_academic_year_start():
                return jsonify({"error": "Arşiv yılındaki kesinleşmiş dağıtım salt okunurdur."}), 403
            if run is None or run.config_hash != _distribution_fingerprint(session, organization):
                return jsonify({"error": "Sınav veya derslik ayarları değişmiş; bu geçmiş kaydı düzenlenemiyor."}), 409
            try:
                _review_selected_candidate(session, organization)
            except ValueError as error:
                return jsonify({"error": str(error)}), 409

            events = session.scalars(
                select(DistributionEvent).where(DistributionEvent.candidate_id == candidate.id)
                .order_by(DistributionEvent.created_at, DistributionEvent.id)
            ).all()
            history = _candidate_history_state(events)
            event_id = history["undo_event_id"] if action == "undo" else history["redo_event_id"]
            if not event_id:
                return jsonify({"error": "Geri alınacak işlem yok." if action == "undo" else "Yinelenecek işlem yok."}), 409
            original = next(event for event in events if event.id == event_id)
            assignments = session.scalars(
                select(SeatAssignment).where(SeatAssignment.candidate_id == candidate.id)
            ).all()
            by_participant = {item.participant_id: item for item in assignments}
            moving = by_participant.get(original.participant_id)
            displaced = by_participant.get(original.displaced_participant_id) if original.displaced_participant_id else None
            if moving is None or (original.displaced_participant_id and displaced is None):
                return jsonify({"error": "İşlemdeki öğrenci bu dağıtımda bulunmuyor."}), 409
            if action == "undo":
                expected_moving, expected_displaced = original.to_seat_id, original.from_seat_id
                moving_target, displaced_target = original.from_seat_id, original.to_seat_id
            else:
                expected_moving, expected_displaced = original.from_seat_id, original.to_seat_id
                moving_target, displaced_target = original.to_seat_id, original.from_seat_id
            if moving.seat_id != expected_moving or (displaced and displaced.seat_id != expected_displaced):
                return jsonify({"error": "Geçmiş işleminin beklenen koltuk durumu bulunamadı; başka bir değişiklikle çakışıyor."}), 409
            source_seat_id = moving.seat_id
            _set_assignment_pair(
                session, assignments, original.participant_id, moving_target,
                original.displaced_participant_id, displaced_target if displaced else None,
            )
            session.add(DistributionEvent(
                candidate_id=candidate.id,
                event_type=action,
                participant_id=original.participant_id,
                displaced_participant_id=original.displaced_participant_id,
                from_seat_id=source_seat_id,
                to_seat_id=moving_target,
                related_event_id=original.id,
            ))
            session.flush()
            review = _review_selected_candidate(session, organization)
            candidate.affected_student_count = review["affected_student_count"]
            result = _serialize_candidate(session, organization, candidate)
            result["review"] = review
            result["report_status"] = report_status(session, organization)["report_status"]
            result["report_statuses"] = all_report_statuses(session, organization)
    except IntegrityError:
        return jsonify({"error": "Geçmiş işlemi uygulanamadı; koltuk durumu çakışıyor."}), 409
    return jsonify({"candidate": result})


@exam_organizations_api.get("/exam-organizations/<organization_id>/final-review")
def review_distribution_candidate(organization_id: str):
    session_factory = current_app.extensions["kelebek_session_factory"]
    with session_factory() as session:
        organization = session.get(ExamOrganization, organization_id)
        if organization is None:
            return jsonify({"error": "Sınav organizasyonu bulunamadı."}), 404
        try:
            review = _review_selected_candidate(session, organization)
        except ValueError as error:
            return jsonify({"error": str(error)}), 409
    return jsonify({"review": review})


@exam_organizations_api.post("/exam-organizations/<organization_id>/finalize")
def finalize_distribution(organization_id: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or payload.get("confirm") is not True:
        return jsonify({"error": "Kesinleştirmek için açık onay gereklidir."}), 400
    if payload.get("physical_layouts_confirmed") is not True:
        return jsonify({
            "error": "Kesinleştirmeden önce seçilen dersliklerin fiziksel masa ve oturma planlarını doğrulayın."
        }), 400
    session_factory = current_app.extensions["kelebek_session_factory"]
    try:
        with session_factory.begin() as session:
            organization = session.get(ExamOrganization, organization_id)
            if organization is None:
                return jsonify({"error": "Sınav organizasyonu bulunamadı."}), 404
            if organization.status != "draft":
                return jsonify({"error": "Bu sınav organizasyonu zaten kesinleştirilmiş."}), 409
            year = session.get(AcademicYear, organization.academic_year_id)
            if year is None or year.start_year < current_academic_year_start():
                return jsonify({"error": "Arşiv yılındaki organizasyon kesinleştirilemez."}), 403
            try:
                review = _review_selected_candidate(session, organization)
            except ValueError as error:
                return jsonify({"error": str(error)}), 409
            if not review["can_finalize"]:
                message = "Bekleyen öğrenci kalmış; herkes koltuğa yerleşmeden kesinleştirilemez." if review["unassigned_count"] else "Beşten fazla öğrenci kural ihlalinden etkileniyor; bu dağıtım kesinleştirilemez."
                return jsonify({"error": message, "review": review}), 409
            organization.status = "completed"
            result = next(item for item in list_organizations(session, organization.academic_year_id) if item["id"] == organization.id)
    except IntegrityError:
        return jsonify({"error": "Kesinleştirme kaydedilemedi; veriler değişmiş olabilir. Yeniden kontrol edin."}), 409
    return jsonify({"organization": result, "review": review})


@exam_organizations_api.get("/exam-organizations/<organization_id>/reports/seating-plan.pdf")
def download_seating_plan_pdf(organization_id: str):
    session_factory = current_app.extensions["kelebek_session_factory"]
    try:
        options = resolve_pdf_options(request.args, default_orientation="landscape")
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    try:
        with session_factory.begin() as session:
            organization = session.get(ExamOrganization, organization_id)
            if organization is None:
                return jsonify({"error": "Sınav organizasyonu bulunamadı."}), 404
            if organization.status != "completed":
                return jsonify({"error": "Oturma planı PDF'i yalnızca kesinleştirilmiş sınavlar için oluşturulur."}), 409
            try:
                review = _review_selected_candidate(session, organization)
            except ValueError as error:
                return jsonify({"error": str(error)}), 409
            if not review["can_finalize"]:
                return jsonify({"error": "Dağıtımın son kontrolü geçerli değil; PDF oluşturulamadı."}), 409
            pdf_bytes = build_seating_plan_pdf(session, organization, review["candidate_id"], options)
            report_file_name = seating_plan_report_filename(organization)
            record_seating_plan_report(
                session, organization, review["candidate_id"],
                report_file_name,
            )
    except ValueError as error:
        return jsonify({"error": str(error)}), 409
    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=False,
        download_name=report_file_name,
    )


def _download_tabular_report(organization_id: str, report_type: str):
    session_factory = current_app.extensions["kelebek_session_factory"]
    builders = {
        ATTENDANCE_REPORT_TYPE: build_attendance_pdf,
        ROOM_STUDENT_LIST_REPORT_TYPE: build_room_student_list_pdf,
        GENERAL_DISTRIBUTION_REPORT_TYPE: build_general_distribution_pdf,
        CLASS_STUDENT_LIST_REPORT_TYPE: build_class_student_list_pdf,
    }
    builder = builders[report_type]
    default_orientation = "landscape" if report_type in {
        ATTENDANCE_REPORT_TYPE, GENERAL_DISTRIBUTION_REPORT_TYPE
    } else "portrait"
    try:
        options = resolve_pdf_options(request.args, default_orientation=default_orientation)
        fields = resolve_report_fields(request.args, report_type)
        labels = resolve_report_labels(request.args, report_type, fields)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    try:
        with session_factory.begin() as session:
            organization = session.get(ExamOrganization, organization_id)
            if organization is None:
                return jsonify({"error": "Sınav organizasyonu bulunamadı."}), 404
            if organization.status != "completed":
                return jsonify({"error": "Rapor yalnızca kesinleştirilmiş sınavlar için oluşturulur."}), 409
            try:
                review = _review_selected_candidate(session, organization)
            except ValueError as error:
                return jsonify({"error": str(error)}), 409
            if not review["can_finalize"]:
                return jsonify({"error": "Dağıtımın son kontrolü geçerli değil; rapor oluşturulamadı."}), 409
            pdf_bytes = builder(session, organization, review["candidate_id"], options, fields, labels)
            file_name = report_filename(organization, report_type)
            record_report(session, organization, review["candidate_id"], report_type, file_name)
    except ValueError as error:
        return jsonify({"error": str(error)}), 409
    return send_file(BytesIO(pdf_bytes), mimetype="application/pdf", as_attachment=False,
                     download_name=file_name)


@exam_organizations_api.get("/exam-organizations/<organization_id>/reports/attendance.pdf")
def download_attendance_pdf(organization_id: str):
    return _download_tabular_report(organization_id, ATTENDANCE_REPORT_TYPE)


@exam_organizations_api.get("/exam-organizations/<organization_id>/reports/room-students.pdf")
def download_room_students_pdf(organization_id: str):
    return _download_tabular_report(organization_id, ROOM_STUDENT_LIST_REPORT_TYPE)


@exam_organizations_api.get("/exam-organizations/<organization_id>/reports/distribution.pdf")
def download_general_distribution_pdf(organization_id: str):
    return _download_tabular_report(organization_id, GENERAL_DISTRIBUTION_REPORT_TYPE)


@exam_organizations_api.get("/exam-organizations/<organization_id>/reports/class-students.pdf")
def download_class_students_pdf(organization_id: str):
    return _download_tabular_report(organization_id, CLASS_STUDENT_LIST_REPORT_TYPE)


def _download_excel_report(organization_id: str, report_type: str):
    session_factory = current_app.extensions["kelebek_session_factory"]
    builders = {
        ROOM_STUDENT_LIST_XLSX_REPORT_TYPE: build_room_student_list_xlsx,
        GENERAL_DISTRIBUTION_XLSX_REPORT_TYPE: build_general_distribution_xlsx,
        CLASS_STUDENT_LIST_XLSX_REPORT_TYPE: build_class_student_list_xlsx,
    }
    try:
        fields = resolve_report_fields(request.args, report_type)
        labels = resolve_report_labels(request.args, report_type, fields)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    try:
        with session_factory() as session:
            organization = session.get(ExamOrganization, organization_id)
            if organization is None:
                return jsonify({"error": "Sınav organizasyonu bulunamadı."}), 404
            if organization.status != "completed":
                return jsonify({"error": "Excel raporu yalnızca kesinleştirilmiş sınavlar için oluşturulur."}), 409
            try:
                review = _review_selected_candidate(session, organization)
            except ValueError as error:
                return jsonify({"error": str(error)}), 409
            if not review["can_finalize"]:
                return jsonify({"error": "Dağıtımın son kontrolü geçerli değil; Excel oluşturulamadı."}), 409
            workbook_bytes = builders[report_type](
                session, organization, review["candidate_id"], fields, labels,
            )
            file_name = report_filename(organization, report_type)
    except ValueError as error:
        return jsonify({"error": str(error)}), 409
    return send_file(BytesIO(workbook_bytes),
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     as_attachment=True, download_name=file_name, max_age=0)


@exam_organizations_api.get("/exam-organizations/<organization_id>/reports/room-students.xlsx")
def download_room_students_xlsx(organization_id: str):
    return _download_excel_report(organization_id, ROOM_STUDENT_LIST_XLSX_REPORT_TYPE)


@exam_organizations_api.get("/exam-organizations/<organization_id>/reports/distribution.xlsx")
def download_general_distribution_xlsx(organization_id: str):
    return _download_excel_report(organization_id, GENERAL_DISTRIBUTION_XLSX_REPORT_TYPE)


@exam_organizations_api.get("/exam-organizations/<organization_id>/reports/class-students.xlsx")
def download_class_students_xlsx(organization_id: str):
    return _download_excel_report(organization_id, CLASS_STUDENT_LIST_XLSX_REPORT_TYPE)
