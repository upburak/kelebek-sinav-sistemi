"""Auditable manual placement changes made to a candidate fork."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from kelebek.db import Base


class DistributionEvent(Base):
    __tablename__ = "distribution_events"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    candidate_id: Mapped[str] = mapped_column(ForeignKey("distribution_candidates.id", ondelete="RESTRICT"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    participant_id: Mapped[str] = mapped_column(ForeignKey("exam_participants.id", ondelete="RESTRICT"), nullable=False)
    displaced_participant_id: Mapped[str | None] = mapped_column(ForeignKey("exam_participants.id", ondelete="RESTRICT"), nullable=True)
    from_seat_id: Mapped[str | None] = mapped_column(ForeignKey("seats.id", ondelete="RESTRICT"), nullable=True)
    to_seat_id: Mapped[str | None] = mapped_column(ForeignKey("seats.id", ondelete="RESTRICT"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
