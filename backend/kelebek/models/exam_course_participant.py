"""Ders ile katılımcı arasındaki çoktan çoğa ilişki."""

from sqlalchemy import ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column

from kelebek.db import Base


class ExamCourseParticipant(Base):
    __tablename__ = "exam_course_participants"
    __table_args__ = (PrimaryKeyConstraint("exam_course_id", "participant_id"),)

    exam_course_id: Mapped[str] = mapped_column(
        ForeignKey("exam_courses.id", ondelete="RESTRICT"), nullable=False
    )
    participant_id: Mapped[str] = mapped_column(
        ForeignKey("exam_participants.id", ondelete="RESTRICT"), nullable=False
    )
