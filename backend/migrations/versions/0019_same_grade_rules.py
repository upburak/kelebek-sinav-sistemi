"""Kural 7-8: aynı sınıf seviyesindeki öğrenciler yan yana/önlü arkalı oturamaz.

Alan bilgisi olmayan 9 ve 10. sınıflarda tek koruma "aynı şube" kuralıydı;
farklı şubelerden iki 9. sınıf öğrencisi yan yana oturabiliyordu. Oysa ikisi de
aynı sınav kağıdını alır. Kullanıcı onayıyla iki kural eklendi (10 Kasım 2026).

Mevcut sınavlarda da açık gelir: güvenli taraf varsayılandır, isteyen sınav
bazında kapatabilir.

Revision ID: 0019_same_grade_rules
Revises: 0018_exam_periods
Create Date: 2026-11-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0019_same_grade_rules"
down_revision = "0018_exam_periods"
branch_labels = None
depends_on = None

ALANLAR = ("prevent_same_grade_adjacent", "prevent_same_grade_front_back")


def upgrade() -> None:
    for alan in ALANLAR:
        op.add_column(
            "exam_organizations",
            sa.Column(alan, sa.Boolean(), nullable=False, server_default=sa.true()),
        )


def downgrade() -> None:
    with op.batch_alter_table("exam_organizations") as batch:
        for alan in reversed(ALANLAR):
            batch.drop_column(alan)
