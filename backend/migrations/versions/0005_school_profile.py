"""Add editable local school identity and administrator records.

Revision ID: 0005_school_profile
Revises: 0004_classroom_layouts
Create Date: 2026-11-07
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_school_profile"
down_revision = "0004_classroom_layouts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "school_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_name", sa.String(length=160), nullable=False),
        sa.Column("province", sa.String(length=100), nullable=False),
        sa.Column("district", sa.String(length=100), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=False),
        sa.Column("phone", sa.String(length=40), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_school_profile_singleton"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "school_administrators",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.CheckConstraint("role IN ('principal', 'vice_principal')", name="ck_school_admin_role"),
        sa.CheckConstraint("display_order >= 0", name="ck_school_admin_order"),
        sa.ForeignKeyConstraint(["profile_id"], ["school_profiles.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("school_administrators")
    op.drop_table("school_profiles")
