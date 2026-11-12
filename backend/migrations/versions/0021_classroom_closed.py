"""Derslik kapatma.

Kullanıcı isteğiyle (13 Kasım 2026) bir derslik silinmeden sınav seçiminden
çıkarılabilir. Kapatılan derslik yeni sınavlarda seçilemez; eski sınavlardaki
yeri ve planları korunur.

Revision ID: 0021_classroom_closed
Revises: 0020_active_layout
Create Date: 2026-11-13
"""

import sqlalchemy as sa
from alembic import op

revision = "0021_classroom_closed"
down_revision = "0020_active_layout"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "classrooms",
        sa.Column("is_closed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    with op.batch_alter_table("classrooms") as batch:
        batch.drop_column("is_closed")
