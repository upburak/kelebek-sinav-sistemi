"""Sınav organizasyonu taslakları ve ders kataloğu API'si."""

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
            result = solve_candidate([{
                "id": item.id, "class_level": item.class_level, "section": item.section,
                "area": item.area, "first_name": item.first_name,
                "last_name": item.last_name, "school_number": item.school_number,
            } for item in participants], rooms, all_pairs, rules)
            run = DistributionRun(organization_id=organization.id, status="completed")
            session.add(run); session.flush()
            candidate = DistributionCandidate(
                run_id=run.id, status=result["status"],
                affected_student_count=result["affected_student_count"],
                objective_value=result["objective"],
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
