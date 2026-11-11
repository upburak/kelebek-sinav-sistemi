"""Bir eğitim-öğretim yılı içinde yürütülen sınav organizasyonu."""

from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from kelebek.db import Base


class ExamOrganization(Base):
    __tablename__ = "exam_organizations"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'completed')", name="ck_exam_organization_status"),
        Index("ix_exam_organizations_year_date", "academic_year_id", "exam_date"),
    )

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    academic_year_id: Mapped[str] = mapped_column(
        ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False
    )
    # 0018 öncesi kayıtlarda boş kalabilir; arayüzde "Dönem atanmamış" altında görünür.
    # Veritabanı düzeyinde yabancı anahtar yok (bkz. migration 0018); bağlantı
    # uygulama katmanında doğrulanır.
    exam_period_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    exam_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    selected_candidate_id: Mapped[str | None] = mapped_column(
        ForeignKey("distribution_candidates.id", ondelete="RESTRICT"), nullable=True
    )
    prevent_same_section_adjacent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    prevent_same_section_front_back: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    prevent_different_grade_same_area_adjacent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    prevent_different_grade_same_area_front_back: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    prevent_same_grade_area_adjacent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    prevent_same_grade_area_front_back: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Kural 7-8 (kullanıcı onayı, 10 Kasım 2026): aynı sınıf seviyesindeki
    # öğrenciler aynı sınav kağıdını aldığı için yan yana/önlü arkalı oturamaz.
    # Alan bilgisi olmayan 9 ve 10. sınıflarda tek koruma "aynı şube" kuralıydı.
    prevent_same_grade_adjacent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    prevent_same_grade_front_back: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    copied_from_organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
