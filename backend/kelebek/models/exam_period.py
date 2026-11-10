"""Sınav dönemi: bir eğitim-öğretim yılı içindeki sınav zamanları.

Her yıl açıldığında dört dönem hazır gelir (Güz 1/2, Bahar 1/2). Adları
değiştirilebilir, yeni dönem eklenebilir, içinde sınav olmayan dönem silinebilir.
Sınav organizasyonları bir döneme bağlanır; böylece liste "hangi sınav ne için"
sorusuna bakılır bakılmaz cevap verir.
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from kelebek.db import Base

# Yeni bir eğitim-öğretim yılı açıldığında hazır gelen dönemler.
DEFAULT_PERIOD_NAMES = (
    "Güz 1. Sınavları",
    "Güz 2. Sınavları",
    "Bahar 1. Sınavları",
    "Bahar 2. Sınavları",
)


class ExamPeriod(Base):
    __tablename__ = "exam_periods"
    __table_args__ = (
        UniqueConstraint("academic_year_id", "name", name="uq_exam_periods_year_name"),
    )

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    academic_year_id: Mapped[str] = mapped_column(
        ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
