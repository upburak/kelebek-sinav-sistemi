"""Öğrenci kayıtlarının dönem bazlı okunması ve tekil eklenmesi."""

import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from kelebek.db import current_academic_year_start
from kelebek.models import AcademicYear, Student, StudentYearEnrollment


AREA_OPTIONS = {"Sayısal", "Eşit Ağırlık", "Sözel", "Dil"}


class StudentRegistryError(ValueError):
    """Kullanıcıya gösterilebilecek öğrenci kayıt doğrulama hatası."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def serialize_enrollment(enrollment: StudentYearEnrollment) -> dict:
    return {
        "id": enrollment.id,
        "student_id": enrollment.student_id,
        "school_number": enrollment.school_number,
        "first_name": enrollment.first_name,
        "last_name": enrollment.last_name,
        "class_level": enrollment.class_level,
        "section": enrollment.section,
        "area": enrollment.area,
        "is_active": enrollment.is_active,
    }


def list_year_students(session: Session, academic_year_id: str, include_inactive: bool = False) -> list[dict]:
    query = select(StudentYearEnrollment).where(
        StudentYearEnrollment.academic_year_id == academic_year_id,
    )
    if not include_inactive:
        query = query.where(StudentYearEnrollment.is_active.is_(True))
    rows = session.scalars(query).all()
    rows.sort(
        key=lambda row: (
            int(row.class_level) if row.class_level.isdigit() else 99,
            row.section.casefold(),
            row.last_name.casefold(),
            row.first_name.casefold(),
            row.school_number.casefold(),
        )
    )
    return [serialize_enrollment(row) for row in rows]


def list_year_student_groups(session: Session, academic_year_id: str) -> list[dict]:
    """Öğrenci adlarını döndürmeden seçilebilir sınıf/şube/alan gruplarını özetle."""
    rows = session.scalars(
        select(StudentYearEnrollment).where(
            StudentYearEnrollment.academic_year_id == academic_year_id,
            StudentYearEnrollment.is_active.is_(True),
        )
    ).all()
    counts = {}
    for row in rows:
        key = (row.class_level, row.section, row.area or "")
        counts[key] = counts.get(key, 0) + 1
    return [
        {"class_level": grade, "section": section, "area": area or None, "student_count": count}
        for (grade, section, area), count in sorted(
            counts.items(),
            key=lambda item: (
                int(item[0][0]) if item[0][0].isdigit() else 99,
                item[0][1].casefold(),
                item[0][2].casefold(),
            ),
        )
    ]


def add_student_to_year(session: Session, academic_year_id: str, payload: dict) -> dict:
    academic_year = session.get(AcademicYear, academic_year_id)
    if academic_year is None:
        raise StudentRegistryError("Seçili eğitim-öğretim yılı bulunamadı.", 404)
    if academic_year.start_year < current_academic_year_start():
        raise StudentRegistryError("Arşiv eğitim yılı salt okunur; öğrenci eklenemez.", 403)

    def clean(field: str, maximum: int) -> str:
        value = payload.get(field)
        if not isinstance(value, str):
            return ""
        return " ".join(value.strip().split())[:maximum]

    school_number = clean("school_number", 64)
    first_name = clean("first_name", 120)
    last_name = clean("last_name", 120)
    class_level = clean("class_level", 32)
    section = clean("section", 32).upper()
    area = clean("area", 120)
    if not all((school_number, first_name, last_name, class_level, section)):
        raise StudentRegistryError("Okul numarası, ad, soyad, sınıf ve şube zorunludur.")
    if class_level not in {"9", "10", "11", "12"}:
        raise StudentRegistryError("Sınıf seviyesi 9, 10, 11 veya 12 olmalıdır.")
    if class_level in {"9", "10"}:
        area = ""
    elif area not in AREA_OPTIONS:
        raise StudentRegistryError("11. ve 12. sınıflar için geçerli bir alan seçin.")

    current = session.scalar(
        select(StudentYearEnrollment).where(
            StudentYearEnrollment.academic_year_id == academic_year_id,
            StudentYearEnrollment.school_number == school_number,
            StudentYearEnrollment.is_active.is_(True),
        )
    )
    if current is not None:
        raise StudentRegistryError("Bu okul numarası seçili yılda zaten kayıtlı.", 409)

    history = session.scalars(
        select(StudentYearEnrollment)
        .where(StudentYearEnrollment.school_number == school_number)
        .order_by(StudentYearEnrollment.created_at.desc())
    ).all()
    if history:
        latest = history[0]
        normalized_name = (first_name.casefold(), last_name.casefold())
        latest_name = (latest.first_name.strip().casefold(), latest.last_name.strip().casefold())
        if latest_name == normalized_name:
            student_id = latest.student_id
        else:
            # A school number may be reassigned later. Never merge the new
            # person with a historical identity when the latest name differs.
            student = Student()
            session.add(student)
            session.flush()
            student_id = student.id
    else:
        student = Student()
        session.add(student)
        session.flush()
        student_id = student.id

    enrollment = StudentYearEnrollment(
        academic_year_id=academic_year_id,
        student_id=student_id,
        school_number=school_number,
        first_name=first_name,
        last_name=last_name,
        class_level=class_level,
        section=section,
        area=area or None,
        is_active=True,
    )
    session.add(enrollment)
    session.flush()
    return serialize_enrollment(enrollment)


def update_student_in_year(session: Session, enrollment: StudentYearEnrollment, payload: dict) -> dict:
    """Correct a current-year student while preserving completed exam snapshots."""
    academic_year = session.get(AcademicYear, enrollment.academic_year_id)
    if academic_year is None:
        raise StudentRegistryError("Eğitim-öğretim yılı bulunamadı.", 404)
    if academic_year.start_year < current_academic_year_start():
        raise StudentRegistryError("Arşiv eğitim yılı salt okunur; öğrenci düzenlenemez.", 403)

    def clean(field: str, maximum: int) -> str:
        value = payload.get(field)
        return " ".join(value.strip().split())[:maximum] if isinstance(value, str) else ""

    school_number = clean("school_number", 64)
    first_name = clean("first_name", 120)
    last_name = clean("last_name", 120)
    class_level = clean("class_level", 32)
    section = clean("section", 32).upper()
    area = clean("area", 120)
    if not all((school_number, first_name, last_name, class_level, section)):
        raise StudentRegistryError("Okul numarası, ad, soyad, sınıf ve şube zorunludur.")
    if class_level not in {"9", "10", "11", "12"}:
        raise StudentRegistryError("Sınıf seviyesi 9, 10, 11 veya 12 olmalıdır.")
    if class_level in {"9", "10"}:
        area = ""
    elif area not in AREA_OPTIONS:
        raise StudentRegistryError("11. ve 12. sınıflar için geçerli bir alan seçin.")

    duplicate = session.scalar(select(StudentYearEnrollment).where(
        StudentYearEnrollment.academic_year_id == enrollment.academic_year_id,
        StudentYearEnrollment.school_number == school_number,
        StudentYearEnrollment.is_active.is_(True),
        StudentYearEnrollment.id != enrollment.id,
    ))
    if duplicate:
        raise StudentRegistryError("Bu okul numarası seçili yılda zaten kayıtlı.", 409)

    enrollment.school_number = school_number
    enrollment.first_name = first_name
    enrollment.last_name = last_name
    enrollment.class_level = class_level
    enrollment.section = section
    enrollment.area = area or None
    sync_draft_exam_snapshots(session, enrollment, deactivate=False)
    session.flush()
    return serialize_enrollment(enrollment)


def deactivate_student_in_year(session: Session, enrollment: StudentYearEnrollment) -> None:
    """Soft-remove a current enrollment and its draft exam participants."""
    academic_year = session.get(AcademicYear, enrollment.academic_year_id)
    if academic_year is None:
        raise StudentRegistryError("Eğitim-öğretim yılı bulunamadı.", 404)
    if academic_year.start_year < current_academic_year_start():
        raise StudentRegistryError("Arşiv eğitim yılı salt okunur; öğrenci çıkarılamaz.", 403)
    if not enrollment.is_active:
        raise StudentRegistryError("Öğrenci zaten pasif.", 409)
    enrollment.is_active = False
    sync_draft_exam_snapshots(session, enrollment, deactivate=True)


def reactivate_student_in_year(session: Session, enrollment: StudentYearEnrollment) -> dict:
    academic_year = session.get(AcademicYear, enrollment.academic_year_id)
    if academic_year is None:
        raise StudentRegistryError("Eğitim-öğretim yılı bulunamadı.", 404)
    if academic_year.start_year < current_academic_year_start():
        raise StudentRegistryError("Arşiv eğitim yılı salt okunur; öğrenci etkinleştirilemez.", 403)
    if enrollment.is_active:
        raise StudentRegistryError("Öğrenci zaten aktif.", 409)
    duplicate = session.scalar(select(StudentYearEnrollment).where(
        StudentYearEnrollment.academic_year_id == enrollment.academic_year_id,
        StudentYearEnrollment.school_number == enrollment.school_number,
        StudentYearEnrollment.is_active.is_(True),
    ))
    if duplicate:
        raise StudentRegistryError("Okul numarası başka bir aktif öğrenciye verilmiş; önce kaydı kontrol edin.", 409)
    enrollment.is_active = True
    sync_draft_exam_snapshots(session, enrollment, deactivate=False, reactivate=True)
    session.flush()
    return serialize_enrollment(enrollment)


def sync_draft_exam_snapshots(
    session: Session,
    enrollment: StudentYearEnrollment,
    *,
    deactivate: bool,
    reactivate: bool = False,
) -> int:
    """Update or deactivate snapshots only in drafts; completed history stays fixed."""
    from kelebek.models import (
        DistributionEvent, DistributionRun, ExamOrganization,
        ExamParticipant, SeatAssignment,
    )

    participants = session.scalars(select(ExamParticipant).where(
        ExamParticipant.enrollment_id == enrollment.id,
    )).all()
    affected = 0
    for participant in participants:
        organization = session.get(ExamOrganization, participant.organization_id)
        if organization is None or organization.status != "draft":
            continue
        if deactivate:
            participant.is_active = False
            selected_candidate_id = organization.selected_candidate_id
            if selected_candidate_id:
                seat_id = session.scalar(select(SeatAssignment.seat_id).where(
                    SeatAssignment.candidate_id == selected_candidate_id,
                    SeatAssignment.participant_id == participant.id,
                ))
                session.add(DistributionEvent(
                    candidate_id=selected_candidate_id,
                    event_type="participant_removed",
                    participant_id=participant.id,
                    from_seat_id=seat_id,
                ))
        else:
            placement_changed = reactivate and not participant.is_active or any(
                getattr(participant, field) != getattr(enrollment, field) for field in ("class_level", "section", "area")
            )
            identity_changed = any(getattr(participant, field) != getattr(enrollment, field)
                                   for field in ("school_number", "first_name", "last_name"))
            participant.school_number = enrollment.school_number
            participant.first_name = enrollment.first_name
            participant.last_name = enrollment.last_name
            participant.class_level = enrollment.class_level
            participant.section = enrollment.section
            participant.area = enrollment.area
            if reactivate:
                participant.is_active = True
            if not placement_changed:
                # Yalnız ad/numara değişikliği komşuluk kurallarını etkilemez; adaylar korunur.
                affected += int(identity_changed)
                continue
        affected += 1
        runs = session.scalars(select(DistributionRun).where(
            DistributionRun.organization_id == organization.id,
        )).all()
        for run in runs:
            run.config_hash = hashlib.sha256(f"invalidated:{run.id}:{uuid.uuid4()}".encode()).hexdigest()
        organization.selected_candidate_id = None
    return affected
