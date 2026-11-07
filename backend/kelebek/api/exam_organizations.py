"""Sınav organizasyonu taslakları ve ders kataloğu API'si."""

import hashlib
import json

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from kelebek.db import current_academic_year_start
from kelebek.models import (
    AcademicYear, Classroom, ClassroomLayout, Desk, DistributionCandidate,
    DistributionRun, ExamOrganization, ExamOrganizationClassroom,
    ExamParticipant, Seat, SeatAssignment,
)
from kelebek.distribution.neighbors import build_neighbor_pairs
from kelebek.distribution.solver import DistributionError, solve_candidate
from kelebek.services.exam_organizer import (
    ExamOrganizerError,
    create_organization,
    list_courses,
    list_organizations,
    list_room_options,
    update_organization_rules,
    update_organization_rooms,
)


exam_organizations_api = Blueprint("exam_organizations", __name__)

RULE_NAMES = (
    "prevent_same_section_adjacent", "prevent_same_section_front_back",
    "prevent_different_grade_same_area_adjacent", "prevent_different_grade_same_area_front_back",
    "prevent_same_grade_area_adjacent", "prevent_same_grade_area_front_back",
)


def _distribution_fingerprint(session, organization):
    participant_rows = session.execute(
        select(ExamParticipant.id, ExamParticipant.class_level, ExamParticipant.section, ExamParticipant.area)
        .where(ExamParticipant.organization_id == organization.id)
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
    session_factory = current_app.extensions["kelebek_session_factory"]
    try:
        with session_factory.begin() as session:
            organization = session.get(ExamOrganization, organization_id)
            if organization is None:
                return jsonify({"error": "Sınav organizasyonu bulunamadı."}), 404
            year = session.get(AcademicYear, organization.academic_year_id)
            if year is None or year.start_year < current_academic_year_start() or organization.status != "draft":
                return jsonify({"error": "Bu organizasyonda dağıtım adayı oluşturulamaz."}), 403
            participants = session.scalars(
                select(ExamParticipant).where(ExamParticipant.organization_id == organization.id)
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
                generation_index = len(previous_candidates) + 1
            else:
                run = DistributionRun(organization_id=organization.id, status="completed", config_hash=config_hash)
                session.add(run); session.flush()
                generation_index = 1
            result = solve_candidate([{
                "id": item.id, "class_level": item.class_level, "section": item.section,
                "area": item.area, "first_name": item.first_name,
                "last_name": item.last_name, "school_number": item.school_number,
            } for item in participants], rooms, all_pairs, rules, previous_assignments=previous_assignments)
            candidate = DistributionCandidate(
                run_id=run.id, status=result["status"],
                affected_student_count=result["affected_student_count"],
                objective_value=result["objective"],
                generation_index=generation_index,
            )
            session.add(candidate); session.flush()
            for assignment in result["assignments"]:
                session.add(SeatAssignment(
                    candidate_id=candidate.id,
                    participant_id=assignment["participant_id"],
                    seat_id=assignment["seat_id"],
                ))
            result["candidate_id"] = candidate.id
            result["run_id"] = run.id
            participant_by_id = {item.id: item for item in participants}
            result["assignments"] = [{
                **item,
                **seat_labels[item["seat_id"]],
                "first_name": participant_by_id[item["participant_id"]].first_name,
                "last_name": participant_by_id[item["participant_id"]].last_name,
                "school_number": participant_by_id[item["participant_id"]].school_number,
                "class_level": participant_by_id[item["participant_id"]].class_level,
                "section": participant_by_id[item["participant_id"]].section,
            } for item in result["assignments"]]
    except DistributionError as error:
        return jsonify({"error": str(error)}), 409
    except IntegrityError:
        return jsonify({"error": "Aday kaydedilemedi; veriler değişmiş olabilir. Yenileyip tekrar deneyin."}), 409
    return jsonify({"candidate": result}), 201


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
            rows = session.execute(
                select(SeatAssignment, ExamParticipant, Seat, Classroom)
                .join(ExamParticipant, ExamParticipant.id == SeatAssignment.participant_id)
                .join(Seat, Seat.id == SeatAssignment.seat_id)
                .join(Desk, Desk.id == Seat.desk_id)
                .join(ClassroomLayout, ClassroomLayout.id == Desk.layout_id)
                .join(Classroom, Classroom.id == ClassroomLayout.classroom_id)
                .where(SeatAssignment.candidate_id == candidate.id)
                .order_by(Classroom.name, Seat.seat_number)
            ).all()
            result.append({
                "candidate_id": candidate.id,
                "run_id": run.id,
                "generation_index": candidate.generation_index,
                "status": candidate.status,
                "affected_student_count": candidate.affected_student_count,
                "assignments": [{
                    "participant_id": assignment.participant_id,
                    "seat_id": seat.id,
                    "seat_number": seat.seat_number,
                    "classroom_id": classroom.id,
                    "classroom_name": classroom.name,
                    "first_name": participant.first_name,
                    "last_name": participant.last_name,
                    "school_number": participant.school_number,
                    "class_level": participant.class_level,
                    "section": participant.section,
                } for assignment, participant, seat, classroom in rows],
            })
    return jsonify({"candidates": result})
