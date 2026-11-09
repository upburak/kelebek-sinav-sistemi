"""A persisted solution candidate produced by a distribution run."""

from uuid import uuid4

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from kelebek.db import Base


class DistributionCandidate(Base):
    __tablename__ = "distribution_candidates"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(ForeignKey("distribution_runs.id", ondelete="RESTRICT"), nullable=False)
    derived_from_candidate_id: Mapped[str | None] = mapped_column(
        ForeignKey("distribution_candidates.id", ondelete="RESTRICT"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    affected_student_count: Mapped[int] = mapped_column(Integer, nullable=False)
    objective_value: Mapped[int] = mapped_column(Integer, nullable=False)
    generation_index: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    pinned_classroom_ids: Mapped[str | None] = mapped_column(Text, nullable=True)
