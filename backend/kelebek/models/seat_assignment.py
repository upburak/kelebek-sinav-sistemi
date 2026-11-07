"""Unique participant-to-seat placement within one candidate."""

from uuid import uuid4

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from kelebek.db import Base


class SeatAssignment(Base):
    __tablename__ = "seat_assignments"
    __table_args__ = (
        UniqueConstraint("candidate_id", "participant_id"),
        UniqueConstraint("candidate_id", "seat_id"),
    )

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    candidate_id: Mapped[str] = mapped_column(ForeignKey("distribution_candidates.id", ondelete="RESTRICT"), nullable=False)
    participant_id: Mapped[str] = mapped_column(ForeignKey("exam_participants.id", ondelete="RESTRICT"), nullable=False)
    seat_id: Mapped[str | None] = mapped_column(ForeignKey("seats.id", ondelete="RESTRICT"), nullable=True)
