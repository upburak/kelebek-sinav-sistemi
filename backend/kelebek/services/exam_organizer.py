"""Sınav organizasyonu taslaklarının iş kuralları."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kelebek.db import current_academic_year_start
from kelebek.models import (
    AcademicYear,
    Course,
    ExamCourse,
    ExamCourseParticipant,
    ExamOrganization,
    ExamParticipant,
    StudentYearEnrollment,
)


class ExamOrganizerError(ValueError):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def list_courses(session: Session) -> list[dict]:
    return [
        {"id": course.id, "name": course.name}
        for course in session.scalars(select(Course).order_by(Course.normalized_name)).all()
    ]


def list_organizations(session: Session, academic_year_id: str) -> list[dict]:
    organizations = session.scalars(
        select(ExamOrganization)
        .where(ExamOrganization.academic_year_id == academic_year_id)
        .order_by(ExamOrganization.exam_date.desc(), ExamOrganization.created_at.desc())
    ).all()
    if not organizations:
        return []
    ids = [item.id for item in organizations]
    course_counts = dict(
        session.execute(
            select(ExamCourse.organization_id, func.count(ExamCourse.id))
            .where(ExamCourse.organization_id.in_(ids))
            .group_by(ExamCourse.organization_id)
        ).all()
    )
    participant_counts = dict(
        session.execute(
            select(ExamParticipant.organization_id, func.count(ExamParticipant.id))
            .where(ExamParticipant.organization_id.in_(ids))
            .group_by(ExamParticipant.organization_id)
        ).all()
    )
    courses_by_org = {}
    course_rows = session.execute(
        select(ExamCourse.organization_id, Course.name)
        .join(Course, Course.id == ExamCourse.course_id)
        .where(ExamCourse.organization_id.in_(ids))
        .order_by(ExamCourse.display_order, Course.normalized_name)
    ).all()
    for organization_id, name in course_rows:
        courses_by_org.setdefault(organization_id, []).append(name)
    return [
        {
            "id": item.id,
            "name": item.name,
            "exam_date": item.exam_date.isoformat(),
            "status": item.status,
            "course_names": courses_by_org.get(item.id, []),
            "course_count": course_counts.get(item.id, 0),
            "participant_count": participant_counts.get(item.id, 0),
        }
        for item in organizations
    ]


def _validated_group(group, available_by_group):
    if not isinstance(group, dict):
        raise ExamOrganizerError("Öğrenci grubu biçimi geçersiz.")
    grade = str(group.get("class_level", "")).strip()
    section = " ".join(str(group.get("section", "")).strip().split()).upper()
    area = " ".join(str(group.get("area") or "").strip().split())
    if grade not in {"9", "10", "11", "12"} or not section:
        raise ExamOrganizerError("Bir sınıf/şube seçimi geçersiz.")
    if grade in {"9", "10"} and area:
        raise ExamOrganizerError("9. ve 10. sınıf gruplarında alan seçilemez.")
    key = (grade, section.casefold(), area.casefold())
    rows = available_by_group.get(key, [])
    if not rows and area:
        raise ExamOrganizerError(f"{grade}/{section} {area} grubu artık öğrenci içermiyor; seçimi yenileyin.", 409)
    if not rows:
        raise ExamOrganizerError(f"{grade}/{section} grubunda aktif öğrenci bulunamadı.", 409)
    return rows


def create_organization(session: Session, payload: dict) -> dict:
    year_id = payload.get("academic_year_id")
    year = session.get(AcademicYear, year_id) if isinstance(year_id, str) else None
    if year is None:
        raise ExamOrganizerError("Seçili eğitim-öğretim yılı bulunamadı.", 404)
    if year.start_year < current_academic_year_start():
        raise ExamOrganizerError("Arşiv yılı salt okunur; yeni organizasyon oluşturulamaz.", 403)

    name = " ".join(str(payload.get("name", "")).strip().split())
    date_value = str(payload.get("exam_date", "")).strip()
    if not name or len(name) > 160:
        raise ExamOrganizerError("Sınav/organizasyon adı gerekli ve 160 karakterden kısa olmalı.")
    try:
        exam_date = date.fromisoformat(date_value)
    except ValueError:
        raise ExamOrganizerError("Geçerli bir sınav tarihi seçin.") from None

    raw_courses = payload.get("courses", [])
    if not isinstance(raw_courses, list):
        raise ExamOrganizerError("Ders seçimleri biçimi geçersiz.")
    raw_general_groups = payload.get("participant_groups", [])
    if not isinstance(raw_general_groups, list):
        raise ExamOrganizerError("Öğrenci grupları biçimi geçersiz.")
    if not raw_courses and not raw_general_groups:
        raise ExamOrganizerError("En az bir sınıf/şube öğrenci grubu seçin.")

    active_enrollments = session.scalars(
        select(StudentYearEnrollment).where(
            StudentYearEnrollment.academic_year_id == year.id,
            StudentYearEnrollment.is_active.is_(True),
        )
    ).all()
    available_by_group = {}
    for enrollment in active_enrollments:
        key = (
            enrollment.class_level,
            enrollment.section.casefold(),
            (enrollment.area or "").casefold(),
        )
        available_by_group.setdefault(key, []).append(enrollment)

    organization = ExamOrganization(
        academic_year_id=year.id,
        name=name,
        exam_date=exam_date,
        status="draft",
    )
    session.add(organization)
    session.flush()

    participants_by_enrollment = {}
    participant_course_pairs = set()

    def include_group(group, exam_course_id=None):
        for enrollment in _validated_group(group, available_by_group):
            participant = participants_by_enrollment.get(enrollment.id)
            if participant is None:
                participant = ExamParticipant(
                    organization_id=organization.id,
                    enrollment_id=enrollment.id,
                    school_number=enrollment.school_number,
                    first_name=enrollment.first_name,
                    last_name=enrollment.last_name,
                    class_level=enrollment.class_level,
                    section=enrollment.section,
                    area=enrollment.area,
                )
                session.add(participant)
                session.flush()
                participants_by_enrollment[enrollment.id] = participant
            if exam_course_id:
                pair = (exam_course_id, participant.id)
                if pair not in participant_course_pairs:
                    session.add(ExamCourseParticipant(
                        exam_course_id=exam_course_id,
                        participant_id=participant.id,
                    ))
                    participant_course_pairs.add(pair)

    if raw_courses:
        seen_names = set()
        for order, raw_course in enumerate(raw_courses):
            if not isinstance(raw_course, dict):
                raise ExamOrganizerError("Ders seçimi biçimi geçersiz.")
            course_name = " ".join(str(raw_course.get("name", "")).strip().split())
            groups = raw_course.get("groups")
            normalized_name = course_name.casefold()
            if not course_name or len(course_name) > 120:
                raise ExamOrganizerError("Her ders için geçerli bir ders adı girin.")
            if normalized_name in seen_names:
                raise ExamOrganizerError("Aynı dersi organizasyona birden fazla eklemeyin.")
            if not isinstance(groups, list) or not groups:
                raise ExamOrganizerError(f"{course_name} dersi için en az bir öğrenci grubu seçin.")
            seen_names.add(normalized_name)

            course = session.scalar(
                select(Course).where(Course.normalized_name == normalized_name)
            )
            if course is None:
                course = Course(name=course_name, normalized_name=normalized_name)
                session.add(course)
                session.flush()
            exam_course = ExamCourse(
                organization_id=organization.id,
                course_id=course.id,
                display_order=order,
            )
            session.add(exam_course)
            session.flush()
            for group in groups:
                include_group(group, exam_course.id)
    else:
        for group in raw_general_groups:
            include_group(group)

    if not participants_by_enrollment:
        raise ExamOrganizerError("Seçilen gruplarda aktif öğrenci bulunamadı.", 409)

    return {
        "id": organization.id,
        "name": organization.name,
        "exam_date": organization.exam_date.isoformat(),
        "status": organization.status,
        "course_names": [
            session.get(Course, item.course_id).name
            for item in session.scalars(
                select(ExamCourse)
                .where(ExamCourse.organization_id == organization.id)
                .order_by(ExamCourse.display_order)
            ).all()
        ],
        "course_count": len(raw_courses),
        "participant_count": len(participants_by_enrollment),
    }
