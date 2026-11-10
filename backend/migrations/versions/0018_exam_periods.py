"""Sınav dönemleri: her eğitim-öğretim yılında hazır gelen sınav zamanları.

Revision ID: 0018_exam_periods
Revises: 0017_exam_archive_and_pins
Create Date: 2026-11-10
"""

from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "0018_exam_periods"
down_revision = "0017_exam_archive_and_pins"
branch_labels = None
depends_on = None

DEFAULT_PERIOD_NAMES = (
    "Güz 1. Sınavları",
    "Güz 2. Sınavları",
    "Bahar 1. Sınavları",
    "Bahar 2. Sınavları",
)


def upgrade() -> None:
    op.create_table(
        "exam_periods",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "academic_year_id",
            sa.String(36),
            sa.ForeignKey("academic_years.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("academic_year_id", "name", name="uq_exam_periods_year_name"),
    )

    # Mevcut sınavlar bir döneme bağlı değildi; alan boş bırakılabilir ve bu
    # kayıtlar arayüzde "Dönem atanmamış" başlığı altında görünür.
    #
    # Sütun veritabanı düzeyinde yabancı anahtar taşımaz. SQLite ALTER ile kısıt
    # eklemeye izin vermiyor; batch kipi ise exam_organizations tablosunu silip
    # yeniden kurmayı gerektiriyor ve bu tabloya bağlı başka tablolar olduğu için
    # silme reddediliyor. Aynı nedenle 0017 de copied_from_organization_id
    # sütununu kısıtsız eklemişti. Bağlantı uygulama katmanında korunur: dönem
    # seçimi oluşturma ve taşıma uçlarında doğrulanır, içinde sınav olan dönem
    # silinemez.
    op.add_column("exam_organizations", sa.Column("exam_period_id", sa.String(36), nullable=True))

    # Var olan her yıl için dört dönemi oluştur; kullanıcı adlarını değiştirebilir.
    connection = op.get_bind()
    years = connection.execute(sa.text("SELECT id FROM academic_years")).fetchall()
    now = datetime.now(UTC).isoformat(sep=" ")
    for (year_id,) in years:
        for order, name in enumerate(DEFAULT_PERIOD_NAMES):
            connection.execute(
                sa.text(
                    "INSERT INTO exam_periods (id, academic_year_id, name, display_order, created_at)"
                    " VALUES (:id, :year, :name, :order, :created)"
                ),
                {"id": str(uuid4()), "year": year_id, "name": name, "order": order, "created": now},
            )


def downgrade() -> None:
    with op.batch_alter_table("exam_organizations") as batch:
        batch.drop_column("exam_period_id")
    op.drop_table("exam_periods")
