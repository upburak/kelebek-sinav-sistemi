"""Karar 39, 68–70: güncel öğrenci karşılaştırması, arşivleme ve çalışma kopyası."""

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from kelebek.db import current_academic_year_start
from kelebek.models import (
    AcademicYear, ClassroomLayout, DistributionCandidate, DistributionEvent, DistributionRun,
    ExamCourse, ExamCourseParticipant, ExamOrganization, ExamOrganizationClassroom,
    ExamParticipant, Seat, SeatAssignment, StudentYearEnrollment,
)
from kelebek.services.exam_organizer import RULE_FIELDS, ExamOrganizerError, list_organizations

COMPARED_FIELDS = ("first_name", "last_name", "class_level", "section", "area")
FIELD_LABELS = {"first_name": "Ad", "last_name": "Soyad", "class_level": "Sınıf seviyesi",
                "section": "Şube", "area": "Alan"}


def _norm(value) -> str:
    return " ".join(str(value or "").split()).casefold()


def current_year(session: Session) -> AcademicYear:
    year = session.scalar(select(AcademicYear).where(AcademicYear.start_year == current_academic_year_start()))
    if year is None:
        raise ExamOrganizerError("Güncel eğitim-öğretim yılı bulunamadı.", 404)
    return year


def _current_enrollment(session: Session, participant: ExamParticipant, year: AcademicYear):
    """Okul numarası ve ad-soyad birlikte eşleşen güncel aktif kaydı bul (Karar 47)."""
    enrollment = session.get(StudentYearEnrollment, participant.enrollment_id)
    if enrollment is not None and enrollment.academic_year_id == year.id:
        return enrollment if enrollment.is_active else None
    candidate = session.scalar(select(StudentYearEnrollment).where(
        StudentYearEnrollment.academic_year_id == year.id,
        StudentYearEnrollment.is_active.is_(True),
        StudentYearEnrollment.school_number == participant.school_number,
    ))
    if candidate is None or _norm(candidate.first_name) != _norm(participant.first_name) \
            or _norm(candidate.last_name) != _norm(participant.last_name):
        return None
    return candidate


def student_changes(session: Session, organization: ExamOrganization) -> list[dict]:
    year = current_year(session)
    participants = session.scalars(select(ExamParticipant).where(
        ExamParticipant.organization_id == organization.id, ExamParticipant.is_active.is_(True),
    ).order_by(ExamParticipant.class_level, ExamParticipant.section, ExamParticipant.school_number)).all()
    seats = {}
    if organization.selected_candidate_id:
        rows = session.execute(select(SeatAssignment.participant_id, Seat.seat_number).outerjoin(
            Seat, Seat.id == SeatAssignment.seat_id,
        ).where(SeatAssignment.candidate_id == organization.selected_candidate_id)).all()
        seats = dict(rows)
    result = []
    for participant in participants:
        enrollment = _current_enrollment(session, participant, year)
        base = {"participant_id": participant.id, "school_number": participant.school_number,
                "name": f"{participant.first_name} {participant.last_name}",
                "class": f"{participant.class_level}/{participant.section}",
                "seat_number": seats.get(participant.id)}
        if enrollment is None:
            result.append({**base, "kind": "left", "changes": []})
            continue
        changes = []
        for field in COMPARED_FIELDS:
            if field == "area" and participant.class_level in {"9", "10"} and enrollment.class_level in {"9", "10"}:
                continue
            old, new = getattr(participant, field), getattr(enrollment, field)
            if _norm(old) != _norm(new):
                changes.append({"field": field, "label": FIELD_LABELS[field], "old": old, "new": new})
        if changes:
            result.append({**base, "kind": "changed", "changes": changes, "enrollment_id": enrollment.id})
    return result


def apply_student_changes(session: Session, organization: ExamOrganization, participant_ids: list[str],
                          fingerprint) -> int:
    """Onaylanan öğrencileri güncelle ve koltuklarını boşaltarak bekleyen havuza al."""
    if organization.status != "completed" or not organization.selected_candidate_id:
        raise ExamOrganizerError("Karşılaştırma yalnızca kesinleşmiş dağıtımda uygulanır.", 409)
    year = current_year(session)
    if organization.academic_year_id != year.id:
        raise ExamOrganizerError("Geçmiş yıl kaydı değiştirilemez; önce çalışma kopyası oluşturun.", 403)
    pending = {item["participant_id"]: item for item in student_changes(session, organization)}
    if not participant_ids or any(item not in pending for item in participant_ids):
        raise ExamOrganizerError("Seçilen öğrencilerden biri için güncel bir fark bulunamadı; listeyi yenileyin.", 409)
    candidate = session.get(DistributionCandidate, organization.selected_candidate_id)
    assignments = {row.participant_id: row for row in session.scalars(
        select(SeatAssignment).where(SeatAssignment.candidate_id == candidate.id)).all()}
    for participant_id in participant_ids:
        participant = session.get(ExamParticipant, participant_id)
        change = pending[participant_id]
        assignment = assignments.get(participant_id)
        from_seat = assignment.seat_id if assignment else None
        if assignment:
            assignment.seat_id = None
        if change["kind"] == "left":
            participant.is_active = False
            event_type = "participant_removed"
        else:
            enrollment = session.get(StudentYearEnrollment, change["enrollment_id"])
            participant.enrollment_id = enrollment.id
            for field in COMPARED_FIELDS:
                setattr(participant, field, getattr(enrollment, field))
            event_type = "student_refresh"
        session.add(DistributionEvent(candidate_id=candidate.id, event_type=event_type,
                                      participant_id=participant_id, from_seat_id=from_seat, to_seat_id=None))
    session.flush()
    candidate.status = "manual"
    session.get(DistributionRun, candidate.run_id).config_hash = fingerprint(session, organization)
    session.flush()
    return len(participant_ids)


def archive_organization(session: Session, organization: ExamOrganization) -> dict:
    if organization.status != "completed":
        raise ExamOrganizerError("Yalnızca kesinleşmiş sınav tamamlanıp arşivlenebilir.", 409)
    if organization.archived_at:
        raise ExamOrganizerError("Bu sınav zaten tamamlandı olarak arşivde.", 409)
    organization.archived_at = datetime.now(timezone.utc)
    session.flush()
    return next(item for item in list_organizations(session, organization.academic_year_id)
                if item["id"] == organization.id)


def _target_layout(session: Session, selection, source_year_id: str, year: AcademicYear):
    if source_year_id == year.id:
        return session.get(ClassroomLayout, selection.layout_id)
    return session.scalar(select(ClassroomLayout).where(
        ClassroomLayout.classroom_id == selection.classroom_id,
        ClassroomLayout.academic_year_id == year.id,
    ).order_by(ClassroomLayout.version.desc()))


def copy_organization(session: Session, source: ExamOrganization, payload: dict) -> dict:
    """Kaynağı değiştirmeden güncel yılda bağımsız bir taslak kopya oluştur (Karar 69)."""
    year = current_year(session)
    name = " ".join(str(payload.get("name", "")).split())
    if not name or len(name) > 160:
        raise ExamOrganizerError("Kopya için 1–160 karakterlik bir ad girin.")
    try:
        exam_date = date.fromisoformat(str(payload.get("exam_date", "")).strip())
    except ValueError:
        raise ExamOrganizerError("Kopya için geçerli bir sınav tarihi seçin.") from None
    copy = ExamOrganization(academic_year_id=year.id, name=name, exam_date=exam_date, status="draft",
                            copied_from_organization_id=source.id,
                            **{field: getattr(source, field) for field in RULE_FIELDS})
    session.add(copy)
    session.flush()
    mapping, skipped = {}, 0
    for participant in session.scalars(select(ExamParticipant).where(
            ExamParticipant.organization_id == source.id, ExamParticipant.is_active.is_(True))).all():
        enrollment = _current_enrollment(session, participant, year)
        if enrollment is None:
            skipped += 1
            continue
        if any(item.enrollment_id == enrollment.id for item in mapping.values()):
            continue
        mapping[participant.id] = ExamParticipant(
            organization_id=copy.id, enrollment_id=enrollment.id, school_number=enrollment.school_number,
            first_name=enrollment.first_name, last_name=enrollment.last_name,
            class_level=enrollment.class_level, section=enrollment.section, area=enrollment.area)
        session.add(mapping[participant.id])
    if not mapping:
        raise ExamOrganizerError("Kaynak sınavdaki öğrencilerin hiçbiri güncel listede bulunamadı.", 409)
    session.flush()
    for exam_course in session.scalars(select(ExamCourse).where(ExamCourse.organization_id == source.id)).all():
        new_course = ExamCourse(organization_id=copy.id, course_id=exam_course.course_id,
                                display_order=exam_course.display_order)
        session.add(new_course)
        session.flush()
        for link in session.scalars(select(ExamCourseParticipant).where(
                ExamCourseParticipant.exam_course_id == exam_course.id)).all():
            if link.participant_id in mapping:
                session.add(ExamCourseParticipant(exam_course_id=new_course.id,
                                                  participant_id=mapping[link.participant_id].id))
    skipped_rooms = 0
    for selection in session.scalars(select(ExamOrganizationClassroom).where(
            ExamOrganizationClassroom.organization_id == source.id)).all():
        layout = _target_layout(session, selection, source.academic_year_id, year)
        if layout is None:
            skipped_rooms += 1
            continue
        session.add(ExamOrganizationClassroom(organization_id=copy.id, classroom_id=selection.classroom_id,
                                              layout_id=layout.id, display_order=selection.display_order))
    session.flush()
    organization = next(item for item in list_organizations(session, year.id) if item["id"] == copy.id)
    return {"organization": organization, "skipped_students": skipped, "skipped_rooms": skipped_rooms,
            "academic_year_id": year.id}
