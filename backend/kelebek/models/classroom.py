"""Okulda sınavlarda kullanılabilecek fiziksel derslik."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from kelebek.db import Base


class Classroom(Base):
    """Fiziksel dersliği, oturma düzeni ve kapasitesinden bağımsız tanımlar."""

    __tablename__ = "classrooms"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
