"""A single optimization execution for an exam organization."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from kelebek.db import Base


class DistributionRun(Base):
    __tablename__ = "distribution_runs"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(ForeignKey("exam_organizations.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
