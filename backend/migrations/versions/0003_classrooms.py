"""Add the physical classrooms registry.

Revision ID: 0003_classrooms
Revises: 0002_student_registry
Create Date: 2026-11-06
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_classrooms"
down_revision = "0002_student_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "classrooms",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )


def downgrade() -> None:
    op.drop_table("classrooms")
