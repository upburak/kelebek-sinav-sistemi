"""Add versioned classroom layouts, physical desks, and individual seats.

Revision ID: 0004_classroom_layouts
Revises: 0003_classrooms
Create Date: 2026-11-06
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_classroom_layouts"
down_revision = "0003_classrooms"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "classroom_layouts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("classroom_id", sa.String(), nullable=False),
        sa.Column("academic_year_id", sa.String(), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("version >= 1", name="ck_layout_version_positive"),
        sa.ForeignKeyConstraint(["academic_year_id"], ["academic_years.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "desks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("layout_id", sa.String(), nullable=False),
        sa.Column("label", sa.String(length=32), nullable=False),
        sa.Column("block_label", sa.String(length=32), nullable=True),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("rotation_degrees", sa.Integer(), nullable=False),
        sa.CheckConstraint("rotation_degrees IN (0, 90, 180, 270)", name="ck_desk_rotation"),
        sa.ForeignKeyConstraint(["layout_id"], ["classroom_layouts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "layout_id", name="uq_desk_id_layout"),
        sa.UniqueConstraint("layout_id", "label", name="uq_desk_label_per_layout"),
    )
    op.create_table(
        "seats",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("layout_id", sa.String(), nullable=False),
        sa.Column("desk_id", sa.String(), nullable=False),
        sa.Column("seat_number", sa.Integer(), nullable=False),
        sa.Column("seat_index", sa.Integer(), nullable=False),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False),
        sa.Column("unavailable_reason", sa.String(length=240), nullable=True),
        sa.CheckConstraint("seat_number >= 1", name="ck_seat_number_positive"),
        sa.CheckConstraint("seat_index >= 1", name="ck_seat_index_positive"),
        sa.ForeignKeyConstraint(["layout_id"], ["classroom_layouts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["desk_id", "layout_id"],
            ["desks.id", "desks.layout_id"],
            ondelete="RESTRICT",
            name="fk_seat_desk_layout",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("layout_id", "seat_number", name="uq_seat_number_per_layout"),
        sa.UniqueConstraint("desk_id", "seat_index", name="uq_seat_index_per_desk"),
    )


def downgrade() -> None:
    op.drop_table("seats")
    op.drop_table("desks")
    op.drop_table("classroom_layouts")
