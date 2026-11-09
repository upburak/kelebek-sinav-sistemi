"""Latest generated report snapshot for an exam organization."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from kelebek.db import Base


class DistributionReport(Base):
    __tablename__ = "distribution_reports"
    __table_args__ = (UniqueConstraint("organization_id", "report_type", name="uq_distribution_report_org_type"),)

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("exam_organizations.id", ondelete="RESTRICT"), nullable=False
    )
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("distribution_candidates.id", ondelete="RESTRICT"), nullable=False
    )
    report_type: Mapped[str] = mapped_column(String(64), nullable=False)
    data_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    file_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
    )
