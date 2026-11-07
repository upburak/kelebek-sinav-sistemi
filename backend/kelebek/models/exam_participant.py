"""Organizasyondaki tekil öğrenci ve değişmez bilgi anlık görüntüsü."""

from uuid import uuid4

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from kelebek.db import Base


class ExamParticipant(Base):
    __tablename__ = "exam_participants"
    __table_args__ = (UniqueConstraint("organization_id", "enrollment_id"),)

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("exam_organizations.id", ondelete="RESTRICT"), nullable=False
    )
    enrollment_id: Mapped[str] = mapped_column(
        ForeignKey("student_year_enrollments.id", ondelete="RESTRICT"), nullable=False
    )
    school_number: Mapped[str] = mapped_column(String(64), nullable=False)
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    class_level: Mapped[str] = mapped_column(String(32), nullable=False)
    section: Mapped[str] = mapped_column(String(32), nullable=False)
    area: Mapped[str | None] = mapped_column(String(120), nullable=True)
