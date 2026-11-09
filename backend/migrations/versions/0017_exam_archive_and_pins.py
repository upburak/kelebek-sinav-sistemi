"""Archive completed exams, track working copies and pinned rooms of alternatives.

Revision ID: 0017_exam_archive_and_pins
Revises: 0016_exam_participant_active
Create Date: 2026-11-09
"""

import sqlalchemy as sa
from alembic import op

revision = "0017_exam_archive_and_pins"
down_revision = "0016_exam_participant_active"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("exam_organizations", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("exam_organizations", sa.Column("copied_from_organization_id", sa.String(36), nullable=True))
    op.add_column("distribution_candidates", sa.Column("pinned_classroom_ids", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("distribution_candidates") as batch:
        batch.drop_column("pinned_classroom_ids")
    with op.batch_alter_table("exam_organizations") as batch:
        batch.drop_column("copied_from_organization_id")
        batch.drop_column("archived_at")
