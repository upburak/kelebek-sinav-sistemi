"""Record the generated PDF checksum and make legacy snapshots verifiable.

Revision ID: 0015_distribution_report_file_hash
Revises: 0014_completed_distribution_edits
Create Date: 2026-11-07
"""

from alembic import op
import sqlalchemy as sa


revision = "0015_distribution_report_file_hash"
down_revision = "0014_completed_distribution_edits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "distribution_reports",
        sa.Column("file_sha256", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("distribution_reports", "file_sha256")
