"""Create academic years table.

Revision ID: 0001_academic_years
Revises:
Create Date: 2026-11-06
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_academic_years"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "academic_years",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("start_year", sa.Integer(), nullable=False),
        sa.Column("end_year", sa.Integer(), nullable=False),
        sa.Column("is_selected", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("end_year = start_year + 1", name="ck_academic_years_consecutive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("start_year"),
    )
    op.create_index(
        "uq_academic_years_selected",
        "academic_years",
        ["is_selected"],
        unique=True,
        sqlite_where=sa.text("is_selected = 1"),
    )


def downgrade() -> None:
    op.drop_index("uq_academic_years_selected", table_name="academic_years")
    op.drop_table("academic_years")
