"""Connect draft exam organizations to selected room layout versions.

Revision ID: 0007_exam_classrooms
Revises: 0006_exam_organizations
Create Date: 2026-11-07
"""

import sqlalchemy as sa
from alembic import op

revision = "0007_exam_classrooms"
down_revision = "0006_exam_organizations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exam_organization_classrooms",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("classroom_id", sa.String(), nullable=False),
        sa.Column("layout_id", sa.String(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["classroom_id"], ["classrooms.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["layout_id"], ["classroom_layouts.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["exam_organizations.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "classroom_id"),
        sa.UniqueConstraint("organization_id", "layout_id"),
    )


def downgrade() -> None:
    op.drop_table("exam_organization_classrooms")
