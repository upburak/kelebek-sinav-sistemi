"""Toplu silme: bir eğitim yılının sınavlarını, öğrencilerini ya da dersliklerini tümüyle sil.

Karar 73 (kullanıcı onayı, 12 Kasım 2026). Öğrenciler ve derslik planları
sınavlara bağlı olduğu için ikisinin silinmesi o yılın sınavlarını da siler.
Arşiv yılları salt okunurdur. Çağıran taraf silmeden önce güvenlik yedeği alır.
"""

from __future__ import annotations

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from kelebek.config import get_data_dir
from kelebek.db import current_academic_year_start
from kelebek.models import (
    AcademicYear,
    Classroom,
    ClassroomLayout,
    Desk,
    DistributionCandidate,
    DistributionEvent,
    DistributionReport,
    DistributionRun,
    ExamCourse,
    ExamCourseParticipant,
    ExamOrganization,
    ExamOrganizationClassroom,
    ExamParticipant,
    Seat,
    SeatAssignment,
    Student,
    StudentYearEnrollment,
)

SCOPES = ("exams", "students", "classrooms")


class BulkDeleteError(ValueError):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def _checked_year(session: Session, academic_year_id: str) -> AcademicYear:
    year = session.get(AcademicYear, academic_year_id) if academic_year_id else None
    if year is None:
        raise BulkDeleteError("Eğitim-öğretim yılı bulunamadı.", 404)
    if year.start_year < current_academic_year_start():
        raise BulkDeleteError("Arşiv yılları salt okunur; toplu silme yalnızca güncel yılda yapılır.", 403)
    return year


def _count(session: Session, model, *conditions) -> int:
    return session.scalar(select(func.count()).select_from(model).where(*conditions)) or 0


def preview(session: Session, scope: str, academic_year_id: str) -> dict[str, int]:
    """Silinecek kayıt sayıları; hiçbir şeyi değiştirmez."""
    if scope not in SCOPES:
        raise BulkDeleteError("Silme kapsamı geçersiz.")
    _checked_year(session, academic_year_id)
    counts = {"exams": _count(session, ExamOrganization, ExamOrganization.academic_year_id == academic_year_id)}
    if scope == "students":
        counts["students"] = _count(session, StudentYearEnrollment,
                                    StudentYearEnrollment.academic_year_id == academic_year_id)
    if scope == "classrooms":
        counts["classrooms"] = session.scalar(
            select(func.count(func.distinct(ClassroomLayout.classroom_id)))
            .where(ClassroomLayout.academic_year_id == academic_year_id)
        ) or 0
    return counts


def _delete_exams(session: Session, academic_year_id: str) -> int:
    exam_ids = select(ExamOrganization.id).where(ExamOrganization.academic_year_id == academic_year_id)
    run_ids = select(DistributionRun.id).where(DistributionRun.organization_id.in_(exam_ids))
    candidate_ids = select(DistributionCandidate.id).where(DistributionCandidate.run_id.in_(run_ids))
    course_ids = select(ExamCourse.id).where(ExamCourse.organization_id.in_(exam_ids))
    count = _count(session, ExamOrganization, ExamOrganization.academic_year_id == academic_year_id)
    if not count:
        return 0

    # Üretilmiş rapor dosyaları da silinir; kayıtları kalmayacağı için sahipsiz kalırlardı.
    export_dir = get_data_dir() / "Exports" / "PDF"
    for file_name in session.scalars(
        select(DistributionReport.file_name).where(DistributionReport.organization_id.in_(exam_ids))
    ).all():
        (export_dir / file_name).unlink(missing_ok=True)

    # Kendine ve birbirine bağlı kayıtlar: önce bağlar çözülür, sonra yapraklardan köke silinir.
    session.execute(update(ExamOrganization).where(ExamOrganization.id.in_(exam_ids))
                    .values(selected_candidate_id=None))
    session.execute(delete(DistributionReport).where(DistributionReport.organization_id.in_(exam_ids)))
    session.execute(update(DistributionEvent).where(DistributionEvent.candidate_id.in_(candidate_ids))
                    .values(related_event_id=None))
    session.execute(delete(DistributionEvent).where(DistributionEvent.candidate_id.in_(candidate_ids)))
    session.execute(delete(SeatAssignment).where(SeatAssignment.candidate_id.in_(candidate_ids)))
    session.execute(update(DistributionCandidate).where(DistributionCandidate.run_id.in_(run_ids))
                    .values(derived_from_candidate_id=None))
    session.execute(delete(DistributionCandidate).where(DistributionCandidate.run_id.in_(run_ids)))
    session.execute(delete(DistributionRun).where(DistributionRun.organization_id.in_(exam_ids)))
    session.execute(delete(ExamCourseParticipant).where(ExamCourseParticipant.exam_course_id.in_(course_ids)))
    session.execute(delete(ExamCourse).where(ExamCourse.organization_id.in_(exam_ids)))
    session.execute(delete(ExamParticipant).where(ExamParticipant.organization_id.in_(exam_ids)))
    session.execute(delete(ExamOrganizationClassroom).where(ExamOrganizationClassroom.organization_id.in_(exam_ids)))
    session.execute(delete(ExamOrganization).where(ExamOrganization.academic_year_id == academic_year_id))
    session.flush()
    return count


def _delete_students(session: Session, academic_year_id: str) -> int:
    count = _count(session, StudentYearEnrollment, StudentYearEnrollment.academic_year_id == academic_year_id)
    session.execute(delete(StudentYearEnrollment)
                    .where(StudentYearEnrollment.academic_year_id == academic_year_id))
    # Başka yılda kaydı kalmayan öğrenci kimlikleri de silinir.
    session.execute(delete(Student).where(Student.id.not_in(select(StudentYearEnrollment.student_id))))
    session.flush()
    return count


def _delete_classrooms(session: Session, academic_year_id: str) -> int:
    layout_ids = select(ClassroomLayout.id).where(ClassroomLayout.academic_year_id == academic_year_id)
    affected = set(session.scalars(
        select(ClassroomLayout.classroom_id).where(ClassroomLayout.academic_year_id == academic_year_id)
    ).all())
    session.execute(delete(Seat).where(Seat.layout_id.in_(layout_ids)))
    session.execute(delete(Desk).where(Desk.layout_id.in_(layout_ids)))
    session.execute(delete(ClassroomLayout).where(ClassroomLayout.academic_year_id == academic_year_id))
    session.flush()
    # Başka yılda planı ya da sınav kaydı kalmayan derslikler, şablonlarıyla birlikte silinir.
    keep = set(session.scalars(
        select(ClassroomLayout.classroom_id).where(ClassroomLayout.academic_year_id.is_not(None))
    ).all()) | set(session.scalars(select(ExamOrganizationClassroom.classroom_id)).all())
    removable = [item for item in session.scalars(select(Classroom.id)).all() if item not in keep]
    if removable:
        template_ids = select(ClassroomLayout.id).where(ClassroomLayout.classroom_id.in_(removable))
        session.execute(delete(Seat).where(Seat.layout_id.in_(template_ids)))
        session.execute(delete(Desk).where(Desk.layout_id.in_(template_ids)))
        session.execute(delete(ClassroomLayout).where(ClassroomLayout.classroom_id.in_(removable)))
        session.execute(delete(Classroom).where(Classroom.id.in_(removable)))
    session.flush()
    return len(affected | set(removable))


def delete_scope(session: Session, scope: str, academic_year_id: str) -> dict[str, int]:
    """Kapsamı sil ve silinen kayıt sayılarını döndür."""
    if scope not in SCOPES:
        raise BulkDeleteError("Silme kapsamı geçersiz.")
    _checked_year(session, academic_year_id)
    deleted = {"exams": _delete_exams(session, academic_year_id)}
    if scope == "students":
        deleted["students"] = _delete_students(session, academic_year_id)
    if scope == "classrooms":
        deleted["classrooms"] = _delete_classrooms(session, academic_year_id)
    return deleted
