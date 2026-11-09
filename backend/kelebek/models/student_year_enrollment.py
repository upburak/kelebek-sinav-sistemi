"""Öğrencinin belirli eğitim yılındaki okul ve sınıf kaydı."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from kelebek.db import Base


class StudentYearEnrollment(Base):
    """Eğitim yılına bağlı öğrenci bilgilerini ve aktiflik durumunu saklar."""

    __tablename__ = "student_year_enrollments"
    __table_args__ = (
        Index(
            "uq_active_enrollment_school_number",
            "academic_year_id",
            "school_number",
            unique=True,
            sqlite_where=text("is_active = 1"),
        ),
    )

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    academic_year_id: Mapped[str] = mapped_column(
        ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False
    )
    student_id: Mapped[str] = mapped_column(
        ForeignKey("students.id", ondelete="RESTRICT"), nullable=False
    )
    school_number: Mapped[str] = mapped_column(String(64), nullable=False)
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    class_level: Mapped[str] = mapped_column(String(32), nullable=False)
    section: Mapped[str] = mapped_column(String(32), nullable=False)
    area: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
