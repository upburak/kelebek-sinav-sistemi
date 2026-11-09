"""Okulun genel kimlik ve iletişim bilgileri."""

from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from kelebek.db import Base


class SchoolProfile(Base):
    """Tek okul için yerel profil kaydı."""

    __tablename__ = "school_profiles"
    __table_args__ = (CheckConstraint("id = 1", name="ck_school_profile_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    school_name: Mapped[str] = mapped_column(String(160), nullable=False)
    province: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    district: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    address: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    phone: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    email: Mapped[str] = mapped_column(String(254), nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class SchoolAdministrator(Base):
    """Okul müdürü ve müdür yardımcıları."""

    __tablename__ = "school_administrators"
    __table_args__ = (
        CheckConstraint("role IN ('principal', 'vice_principal')", name="ck_school_admin_role"),
        CheckConstraint("display_order >= 0", name="ck_school_admin_order"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("school_profiles.id", ondelete="RESTRICT"), nullable=False, default=1
    )
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
