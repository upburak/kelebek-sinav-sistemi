"""Eğitim-öğretim yılı modeli."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from kelebek.db import Base


class AcademicYear(Base):
    """Bir eğitim-öğretim yılını ve seçili çalışma yılını temsil eder."""

    __tablename__ = "academic_years"
    __table_args__ = (
        CheckConstraint("end_year = start_year + 1", name="ck_academic_years_consecutive"),
        Index(
            "uq_academic_years_selected",
            "is_selected",
            unique=True,
            sqlite_where=text("is_selected = 1"),
        ),
    )

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    start_year: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    end_year: Mapped[int] = mapped_column(Integer, nullable=False)
    is_selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    @property
    def label(self) -> str:
        """Kullanıcıya gösterilen yıl aralığı."""
        return f"{self.start_year}-{self.end_year}"
