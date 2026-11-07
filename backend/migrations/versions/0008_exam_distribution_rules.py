"""Add per-exam seating-neighbor rule settings.

Revision ID: 0008_exam_distribution_rules
Revises: 0007_exam_classrooms
Create Date: 2026-11-07
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_exam_distribution_rules"
down_revision = "0007_exam_classrooms"
branch_labels = None
depends_on = None


RULE_COLUMNS = (
    "prevent_same_section_adjacent",
    "prevent_same_section_front_back",
    "prevent_different_grade_same_area_adjacent",
    "prevent_different_grade_same_area_front_back",
    "prevent_same_grade_area_adjacent",
    "prevent_same_grade_area_front_back",
)


def upgrade() -> None:
    for name in RULE_COLUMNS:
        op.add_column(
            "exam_organizations",
            sa.Column(name, sa.Boolean(), nullable=False, server_default=sa.true()),
        )


def downgrade() -> None:
    for name in reversed(RULE_COLUMNS):
        op.drop_column("exam_organizations", name)
