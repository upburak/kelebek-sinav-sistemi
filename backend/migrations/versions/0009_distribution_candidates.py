"""Persist distribution runs and their seat assignments.

Revision ID: 0009_distribution_candidates
Revises: 0008_exam_distribution_rules
Create Date: 2026-11-07
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_distribution_candidates"
down_revision = "0008_exam_distribution_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "distribution_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["exam_organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "distribution_candidates",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("affected_student_count", sa.Integer(), nullable=False),
        sa.Column("objective_value", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["distribution_runs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "seat_assignments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("candidate_id", sa.String(), nullable=False),
        sa.Column("participant_id", sa.String(), nullable=False),
        sa.Column("seat_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["distribution_candidates.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["participant_id"], ["exam_participants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["seat_id"], ["seats.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("candidate_id", "participant_id"),
        sa.UniqueConstraint("candidate_id", "seat_id"),
    )


def downgrade() -> None:
    op.drop_table("seat_assignments")
    op.drop_table("distribution_candidates")
    op.drop_table("distribution_runs")
