"""Store candidate ancestry and auditable manual moves.

Revision ID: 0012_candidate_manual_edits
Revises: 0011_select_distribution_candidate
Create Date: 2026-11-07
"""

import sqlalchemy as sa
from alembic import op

revision = "0012_candidate_manual_edits"
down_revision = "0011_select_distribution_candidate"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("distribution_candidates") as batch_op:
        batch_op.add_column(sa.Column("derived_from_candidate_id", sa.String(), nullable=True))
        batch_op.create_foreign_key(
            "fk_distribution_candidates_parent",
            "distribution_candidates",
            ["derived_from_candidate_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    op.create_table(
        "distribution_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("candidate_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("participant_id", sa.String(), nullable=False),
        sa.Column("displaced_participant_id", sa.String(), nullable=True),
        sa.Column("from_seat_id", sa.String(), nullable=False),
        sa.Column("to_seat_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["distribution_candidates.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["participant_id"], ["exam_participants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["displaced_participant_id"], ["exam_participants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["from_seat_id"], ["seats.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["to_seat_id"], ["seats.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("distribution_events")
    with op.batch_alter_table("distribution_candidates") as batch_op:
        batch_op.drop_constraint("fk_distribution_candidates_parent", type_="foreignkey")
        batch_op.drop_column("derived_from_candidate_id")
