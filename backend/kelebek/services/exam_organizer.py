"""Sınav organizasyonu taslaklarının iş kuralları."""

import re
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kelebek.db import current_academic_year_start
from kelebek.models import (
    AcademicYear,
    Classroom,
    ClassroomLayout,
    Course,
    ExamCourse,
    ExamCourseParticipant,
    ExamOrganization,
    ExamOrganizationClassroom,
    ExamParticipant,
    ExamPeriod,
    Seat,
    StudentYearEnrollment,
)
from kelebek.services.reporting import REPORT_TYPES, all_report_statuses


class ExamOrganizerError(ValueError):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


RULE_FIELDS = (
    "prevent_same_grade_adjacent",
    "prevent_same_grade_front_back",
    "prevent_same_section_adjacent",
    "prevent_same_section_front_back",
    "prevent_different_grade_same_area_adjacent",
    "prevent_different_grade_same_area_front_back",
    "prevent_same_grade_area_adjacent",
    "prevent_same_grade_area_front_back",
)


def _serialize_rules(organization: ExamOrganization) -> dict[str, bool]:
    return {field: bool(getattr(organization, field)) for field in RULE_FIELDS}


def list_courses(session: Session) -> list[dict]:
    return [
        {"id": course.id, "name": course.name}
        for course in session.scalars(select(Course).order_by(Course.normalized_name)).all()
    ]


def _layout_capacity(session: Session, layout_id: str) -> tuple[int, int]:
    total = session.scalar(
        select(func.count(Seat.id)).where(Seat.layout_id == layout_id)
    ) or 0
    available = session.scalar(
        select(func.count(Seat.id)).where(
            Seat.layout_id == layout_id,
            Seat.is_available.is_(True),
        )
    ) or 0
    return total, available


def natural_sort_key(text: str) -> list:
    """Adlardaki sayıları sayı olarak sıralar: "9-A" < "10-A"."""
    return [(0, int(part), "") if part.isdigit() else (1, 0, part.casefold())
            for part in re.split(r"(\d+)", text) if part]


def list_room_options(session: Session, academic_year_id: str) -> list[dict]:
    """Seçili eğitim yılının fiziksel düzen sürümlerini ve kapasitelerini döndür."""
    layouts = session.execute(
        select(ClassroomLayout, Classroom)
        .join(Classroom, Classroom.id == ClassroomLayout.classroom_id)
        .where(ClassroomLayout.academic_year_id == academic_year_id)
        .order_by(Classroom.name, ClassroomLayout.name, ClassroomLayout.version.desc())
    ).all()
    result = []
    for layout, classroom in layouts:
        total, available = _layout_capacity(session, layout.id)
        latest_version = session.scalar(
            select(func.max(ClassroomLayout.version)).where(
                ClassroomLayout.classroom_id == layout.classroom_id,
                ClassroomLayout.name == layout.name,
                ClassroomLayout.academic_year_id == academic_year_id,
            )
        )
        result.append({
            "classroom_id": classroom.id,
            "classroom_name": classroom.name,
            "layout_id": layout.id,
            "layout_name": layout.name,
            "version": layout.version,
            "total_seats": total,
            "available_seats": available,
            "can_select": total > 0,
            "is_latest": layout.version == latest_version,
        })
    # "9-A", "10-A"dan önce gelir; aynı dersliğin düzenleri kendi sırasını korur.
    result.sort(key=lambda item: natural_sort_key(item["classroom_name"]))
    return result


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
            .where(
                ExamParticipant.organization_id.in_(ids),
                ExamParticipant.is_active.is_(True),
            )
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
    room_selections_by_org = {}
    room_rows = session.execute(
        select(ExamOrganizationClassroom, Classroom, ClassroomLayout)
        .join(Classroom, Classroom.id == ExamOrganizationClassroom.classroom_id)
        .join(ClassroomLayout, ClassroomLayout.id == ExamOrganizationClassroom.layout_id)
        .where(ExamOrganizationClassroom.organization_id.in_(ids))
        .order_by(ExamOrganizationClassroom.display_order, Classroom.name)
    ).all()
    for selection, classroom, layout in room_rows:
        _total, available = _layout_capacity(session, layout.id)
        room_selections_by_org.setdefault(selection.organization_id, []).append({
            "classroom_id": classroom.id,
            "classroom_name": classroom.name,
            "layout_id": layout.id,
            "layout_name": layout.name,
            "version": layout.version,
            "available_seats": available,
        })
    report_status_by_org = {
        item.id: all_report_statuses(session, item) if item.status == "completed"
        else {kind: {"report_status": "not_generated", "report_updated_at": None}
              for kind in REPORT_TYPES}
        for item in organizations
    }
    period_names = dict(
        session.execute(select(ExamPeriod.id, ExamPeriod.name)).all()
    )
    return [
        {
            "id": item.id,
            "name": item.name,
            "exam_period_id": item.exam_period_id,
            "exam_period_name": period_names.get(item.exam_period_id),
            "exam_date": item.exam_date.isoformat(),
            "status": item.status,
            "course_names": courses_by_org.get(item.id, []),
            "course_count": course_counts.get(item.id, 0),
            "participant_count": participant_counts.get(item.id, 0),
            "room_selections": room_selections_by_org.get(item.id, []),
            "available_capacity": sum(
                room["available_seats"] for room in room_selections_by_org.get(item.id, [])
            ),
            "capacity_sufficient": bool(room_selections_by_org.get(item.id)) and sum(
                room["available_seats"] for room in room_selections_by_org.get(item.id, [])
            ) >= participant_counts.get(item.id, 0),
            "capacity_deficit": max(
                0,
                participant_counts.get(item.id, 0) - sum(
                    room["available_seats"] for room in room_selections_by_org.get(item.id, [])
                ),
            ),
            "rules": _serialize_rules(item),
            "selected_candidate_id": item.selected_candidate_id,
            "archived_at": item.archived_at.isoformat() if item.archived_at else None,
            "copied_from_organization_id": item.copied_from_organization_id,
            "report_status": report_status_by_org[item.id].get("seating_plan_pdf", {}).get("report_status", "not_generated"),
            "report_updated_at": report_status_by_org[item.id].get("seating_plan_pdf", {}).get("report_updated_at"),
            "report_statuses": report_status_by_org[item.id],
        }
        for item in organizations
    ]


def update_organization_rooms(session: Session, organization_id: str, payload: dict) -> dict:
    organization = session.get(ExamOrganization, organization_id)
    if organization is None:
        raise ExamOrganizerError("Sınav organizasyonu bulunamadı.", 404)
    year = session.get(AcademicYear, organization.academic_year_id)
    if year is None:
        raise ExamOrganizerError("Organizasyonun eğitim-öğretim yılı bulunamadı.", 404)
    if year.start_year < current_academic_year_start() or organization.status != "draft":
        raise ExamOrganizerError("Bu organizasyon salt okunur; derslik seçimi değiştirilemez.", 403)

    layout_ids = payload.get("layout_ids")
    if not isinstance(layout_ids, list) or any(not isinstance(item, str) for item in layout_ids):
        raise ExamOrganizerError("Derslik düzeni seçimleri geçersiz.")
    if len(layout_ids) != len(set(layout_ids)):
        raise ExamOrganizerError("Aynı oturma düzenini birden fazla seçmeyin.")
    layouts = session.scalars(
        select(ClassroomLayout).where(ClassroomLayout.id.in_(layout_ids))
    ).all() if layout_ids else []
    if len(layouts) != len(layout_ids):
        raise ExamOrganizerError("Seçilen derslik düzenlerinden biri bulunamadı; seçimi yenileyin.", 409)

    classroom_ids = set()
    for layout in layouts:
        if layout.academic_year_id != organization.academic_year_id:
            raise ExamOrganizerError("Yalnızca bu eğitim yılı için oluşturulmuş derslik düzenleri seçilebilir.", 409)
        _total, available = _layout_capacity(session, layout.id)
        if available == 0:
            raise ExamOrganizerError("Oturulabilir yeri olmayan bir derslik düzeni seçilemez.")
        if layout.classroom_id in classroom_ids:
            raise ExamOrganizerError("Her fiziksel derslik için yalnızca bir oturma düzeni seçin.")
        classroom_ids.add(layout.classroom_id)
    session.query(ExamOrganizationClassroom).filter_by(organization_id=organization.id).delete()
    organization.selected_candidate_id = None
    for order, layout in enumerate(layouts):
        session.add(ExamOrganizationClassroom(
            organization_id=organization.id,
            classroom_id=layout.classroom_id,
            layout_id=layout.id,
            display_order=order,
        ))
    session.flush()
    return next(
        item for item in list_organizations(session, organization.academic_year_id)
        if item["id"] == organization.id
    )


def update_organization_rules(session: Session, organization_id: str, payload: dict) -> dict:
    organization = session.get(ExamOrganization, organization_id)
    if organization is None:
        raise ExamOrganizerError("Sınav organizasyonu bulunamadı.", 404)
    year = session.get(AcademicYear, organization.academic_year_id)
    if year is None:
        raise ExamOrganizerError("Organizasyonun eğitim-öğretim yılı bulunamadı.", 404)
    if year.start_year < current_academic_year_start() or organization.status != "draft":
        raise ExamOrganizerError("Bu organizasyon salt okunur; dağıtım kuralları değiştirilemez.", 403)
    rules = payload.get("rules")
    if not isinstance(rules, dict) or set(rules) != set(RULE_FIELDS):
        raise ExamOrganizerError("Altı dağıtım kuralının tamamı gönderilmelidir.")
    if any(type(value) is not bool for value in rules.values()):
        raise ExamOrganizerError("Dağıtım kuralları yalnızca açık veya kapalı olabilir.")
    for field in RULE_FIELDS:
        setattr(organization, field, rules[field])
    organization.selected_candidate_id = None
    session.flush()
    return next(
        item for item in list_organizations(session, organization.academic_year_id)
        if item["id"] == organization.id
    )


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

    # Her sınav bir döneme bağlanır; böylece liste hangi sınavın ne için
    # yapıldığını gösterir. Dönemler yıl açılırken hazır gelir.
    period_id = payload.get("exam_period_id")
    period = session.get(ExamPeriod, period_id) if isinstance(period_id, str) and period_id else None
    if period is None:
        raise ExamOrganizerError("Sınav dönemi seçin.")
    if period.academic_year_id != year.id:
        raise ExamOrganizerError("Seçilen dönem bu eğitim-öğretim yılına ait değil.")
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
        exam_period_id=period.id,
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

    period = session.get(ExamPeriod, organization.exam_period_id) if organization.exam_period_id else None
    return {
        "id": organization.id,
        "name": organization.name,
        "exam_period_id": organization.exam_period_id,
        "exam_period_name": period.name if period else None,
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
        "room_selections": [],
        "available_capacity": 0,
        "capacity_sufficient": False,
        "capacity_deficit": len(participants_by_enrollment),
        "rules": {field: True for field in RULE_FIELDS},
        "selected_candidate_id": None,
        "archived_at": None,
        "copied_from_organization_id": None,
    }
