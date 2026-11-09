"""Retain removed participants in history while excluding them from draft distributions.

Revision ID: 0016_exam_participant_active
Revises: 0015_distribution_report_file_hash
Create Date: 2026-11-08
"""

import sqlalchemy as sa
from alembic import op

revision = "0016_exam_participant_active"
down_revision = "0015_distribution_report_file_hash"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "exam_participants",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("exam_participants", "is_active")
