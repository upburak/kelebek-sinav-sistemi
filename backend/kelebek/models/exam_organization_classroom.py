"""Sınav organizasyonunda kullanılan derslik ve düzen sürümü."""

from uuid import uuid4

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from kelebek.db import Base


class ExamOrganizationClassroom(Base):
    __tablename__ = "exam_organization_classrooms"
    __table_args__ = (
        UniqueConstraint("organization_id", "classroom_id"),
        UniqueConstraint("organization_id", "layout_id"),
    )

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("exam_organizations.id", ondelete="RESTRICT"), nullable=False
    )
    classroom_id: Mapped[str] = mapped_column(
        ForeignKey("classrooms.id", ondelete="RESTRICT"), nullable=False
    )
    layout_id: Mapped[str] = mapped_column(
        ForeignKey("classroom_layouts.id", ondelete="RESTRICT"), nullable=False
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
