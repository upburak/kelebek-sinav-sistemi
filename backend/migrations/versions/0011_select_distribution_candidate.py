"""Record the candidate under review for an exam organization.

Revision ID: 0011_select_distribution_candidate
Revises: 0010_distribution_alternatives
Create Date: 2026-11-07
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_select_distribution_candidate"
down_revision = "0010_distribution_alternatives"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("exam_organizations") as batch_op:
        batch_op.add_column(sa.Column("selected_candidate_id", sa.String(), nullable=True))
        batch_op.create_foreign_key(
            "fk_exam_organizations_selected_candidate",
            "distribution_candidates",
            ["selected_candidate_id"],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    with op.batch_alter_table("exam_organizations") as batch_op:
        batch_op.drop_constraint("fk_exam_organizations_selected_candidate", type_="foreignkey")
        batch_op.drop_column("selected_candidate_id")
