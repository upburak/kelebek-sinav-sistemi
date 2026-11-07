"""Öğrenci kayıtlarının dönem bazlı okunması ve tekil eklenmesi."""

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


def list_year_students(session: Session, academic_year_id: str) -> list[dict]:
    rows = session.scalars(
        select(StudentYearEnrollment).where(
            StudentYearEnrollment.academic_year_id == academic_year_id,
            StudentYearEnrollment.is_active.is_(True),
        )
    ).all()
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
        normalized_name = (first_name.casefold(), last_name.casefold())
        matching_history = [
            row
            for row in history
            if (row.first_name.strip().casefold(), row.last_name.strip().casefold())
            == normalized_name
        ]
        if not matching_history:
            raise StudentRegistryError(
                "Bu okul numarası başka bir öğrenci kaydında kullanılmış. Yanlış kişiyi birleştirmemek için ekleme durduruldu.",
                409,
            )
        student_id = matching_history[0].student_id
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
