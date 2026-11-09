"""Fiziksel masaya bağlı tekil oturma yeri."""

from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from kelebek.db import Base


class Seat(Base):
    """Oturma yeri numarası, koordinatı ve kullanılabilirliğini saklar."""

    __tablename__ = "seats"
    __table_args__ = (
        ForeignKeyConstraint(
            ["desk_id", "layout_id"],
            ["desks.id", "desks.layout_id"],
            ondelete="RESTRICT",
            name="fk_seat_desk_layout",
        ),
        CheckConstraint("seat_number >= 1", name="ck_seat_number_positive"),
        CheckConstraint("seat_index >= 1", name="ck_seat_index_positive"),
        UniqueConstraint("layout_id", "seat_number", name="uq_seat_number_per_layout"),
        UniqueConstraint("desk_id", "seat_index", name="uq_seat_index_per_desk"),
    )

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    layout_id: Mapped[str] = mapped_column(
        ForeignKey("classroom_layouts.id", ondelete="RESTRICT"), nullable=False
    )
    desk_id: Mapped[str] = mapped_column(String(), nullable=False)
    seat_number: Mapped[int] = mapped_column(Integer, nullable=False)
    seat_index: Mapped[int] = mapped_column(Integer, nullable=False)
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    unavailable_reason: Mapped[str | None] = mapped_column(String(240), nullable=True)
