"""Allow participants to wait in the candidate pool without a seat.

Revision ID: 0013_candidate_waiting_pool
Revises: 0012_candidate_manual_edits
Create Date: 2026-11-07
"""

import sqlalchemy as sa
from alembic import op

revision = "0013_candidate_waiting_pool"
down_revision = "0012_candidate_manual_edits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("seat_assignments") as batch_op:
        batch_op.alter_column("seat_id", existing_type=sa.String(), nullable=True)
    with op.batch_alter_table("distribution_events") as batch_op:
        batch_op.alter_column("from_seat_id", existing_type=sa.String(), nullable=True)
        batch_op.alter_column("to_seat_id", existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("distribution_events") as batch_op:
        batch_op.alter_column("from_seat_id", existing_type=sa.String(), nullable=False)
        batch_op.alter_column("to_seat_id", existing_type=sa.String(), nullable=False)
    with op.batch_alter_table("seat_assignments") as batch_op:
        batch_op.alter_column("seat_id", existing_type=sa.String(), nullable=False)
