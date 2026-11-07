"""Track candidate alternatives against a frozen distribution configuration.

Revision ID: 0010_distribution_alternatives
Revises: 0009_distribution_candidates
Create Date: 2026-11-07
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_distribution_alternatives"
down_revision = "0009_distribution_candidates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("distribution_runs", sa.Column("config_hash", sa.String(length=64), nullable=False, server_default=""))
    op.add_column("distribution_candidates", sa.Column("generation_index", sa.Integer(), nullable=False, server_default="1"))


def downgrade() -> None:
    op.drop_column("distribution_candidates", "generation_index")
    op.drop_column("distribution_runs", "config_hash")
