"""Derslik düzenindeki fiziksel masa veya sıranın konumu."""

from uuid import uuid4

from sqlalchemy import CheckConstraint, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from kelebek.db import Base


class Desk(Base):
    """Masa koordinatı ve blok bilgisini oturma yerlerinden bağımsız tutar."""

    __tablename__ = "desks"
    __table_args__ = (
        CheckConstraint("rotation_degrees IN (0, 90, 180, 270)", name="ck_desk_rotation"),
        UniqueConstraint("id", "layout_id", name="uq_desk_id_layout"),
        UniqueConstraint("layout_id", "label", name="uq_desk_label_per_layout"),
    )

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    layout_id: Mapped[str] = mapped_column(
        ForeignKey("classroom_layouts.id", ondelete="RESTRICT"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(32), nullable=False)
    block_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)
    rotation_degrees: Mapped[int] = mapped_column(nullable=False, default=0)
