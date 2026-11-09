"""Dersliğin yıl bazlı veya yeniden kullanılabilir fiziksel düzen sürümü."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from kelebek.db import Base


class ClassroomLayout(Base):
    """Bir fiziksel derslik için değiştirilebilir, sürümlü plan kaydı."""

    __tablename__ = "classroom_layouts"
    __table_args__ = (CheckConstraint("version >= 1", name="ck_layout_version_positive"),)

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    classroom_id: Mapped[str] = mapped_column(
        ForeignKey("classrooms.id", ondelete="RESTRICT"), nullable=False
    )
    academic_year_id: Mapped[str | None] = mapped_column(
        ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
