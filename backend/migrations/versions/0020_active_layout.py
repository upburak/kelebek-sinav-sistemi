"""Derslik başına etkin oturma düzeni.

Bir derslikte aynı yıl için birden fazla düzen ve sürüm bulunabiliyor, ama
sınavda hangisinin kullanılacağı belli değildi. Kullanıcı isteğiyle (11 Kasım
2026) her derslik ve eğitim yılı için tek bir "aktif düzen" işaretlenir.

Mevcut verilerde her derslik/yıl için en son oluşturulan düzen aktif yapılır;
böylece güncelleme sonrası davranış değişmez.

Revision ID: 0020_active_layout
Revises: 0019_same_grade_rules
Create Date: 2026-11-11
"""

import sqlalchemy as sa
from alembic import op

revision = "0020_active_layout"
down_revision = "0019_same_grade_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "classroom_layouts",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    connection = op.get_bind()
    rows = connection.execute(sa.text(
        "SELECT id, classroom_id, academic_year_id FROM classroom_layouts "
        "WHERE academic_year_id IS NOT NULL ORDER BY created_at DESC, version DESC"
    )).fetchall()
    seen = set()
    for layout_id, classroom_id, academic_year_id in rows:
        key = (classroom_id, academic_year_id)
        if key in seen:
            continue
        seen.add(key)
        connection.execute(
            sa.text("UPDATE classroom_layouts SET is_active = 1 WHERE id = :id"), {"id": layout_id}
        )


def downgrade() -> None:
    with op.batch_alter_table("classroom_layouts") as batch:
        batch.drop_column("is_active")
