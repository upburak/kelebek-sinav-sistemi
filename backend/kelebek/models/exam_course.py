"""Bir organizasyondaki ders kaydı."""

from uuid import uuid4

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from kelebek.db import Base


class ExamCourse(Base):
    __tablename__ = "exam_courses"
    __table_args__ = (UniqueConstraint("organization_id", "course_id"),)

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("exam_organizations.id", ondelete="RESTRICT"), nullable=False
    )
    course_id: Mapped[str] = mapped_column(
        ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
