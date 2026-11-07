"""Bir eğitim-öğretim yılı içinde yürütülen sınav organizasyonu."""

from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from kelebek.db import Base


class ExamOrganization(Base):
    __tablename__ = "exam_organizations"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'completed')", name="ck_exam_organization_status"),
        Index("ix_exam_organizations_year_date", "academic_year_id", "exam_date"),
    )

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    academic_year_id: Mapped[str] = mapped_column(
        ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    exam_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    selected_candidate_id: Mapped[str | None] = mapped_column(
        ForeignKey("distribution_candidates.id", ondelete="RESTRICT"), nullable=True
    )
    prevent_same_section_adjacent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    prevent_same_section_front_back: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    prevent_different_grade_same_area_adjacent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    prevent_different_grade_same_area_front_back: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    prevent_same_grade_area_adjacent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    prevent_same_grade_area_front_back: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
