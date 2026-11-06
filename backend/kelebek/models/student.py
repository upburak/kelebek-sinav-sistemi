"""Öğrencinin eğitim yılları boyunca değişmeyen iç kimliği."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from kelebek.db import Base


class Student(Base):
    """Öğrenci kimliğini kişisel alanlardan ayrı bir ana kayıt olarak tutar."""

    __tablename__ = "students"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
