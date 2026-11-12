"""Okulda sınavlarda kullanılabilecek fiziksel derslik."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String, false
from sqlalchemy.orm import Mapped, mapped_column

from kelebek.db import Base


class Classroom(Base):
    """Fiziksel dersliği, oturma düzeni ve kapasitesinden bağımsız tanımlar."""

    __tablename__ = "classrooms"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    # Kapatılan derslik yeni sınavlarda seçilemez; geçmişi ve planları korunur.
    is_closed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
