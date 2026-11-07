"""Track reversible post-finalization edits and report snapshots.

Revision ID: 0014_completed_distribution_edits
Revises: 0013_candidate_waiting_pool
Create Date: 2026-11-07
"""

from alembic import op
import sqlalchemy as sa


revision = "0014_completed_distribution_edits"
down_revision = "0013_candidate_waiting_pool"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("distribution_events") as batch_op:
        batch_op.add_column(sa.Column("related_event_id", sa.String(), nullable=True))
        batch_op.create_foreign_key(
            "fk_distribution_events_related_event_id",
            "distribution_events",
            ["related_event_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    op.create_table(
        "distribution_reports",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("candidate_id", sa.String(), nullable=False),
        sa.Column("report_type", sa.String(length=64), nullable=False),
        sa.Column("data_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["distribution_candidates.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["exam_organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "report_type", name="uq_distribution_report_org_type"),
    )


def downgrade() -> None:
    op.drop_table("distribution_reports")
    with op.batch_alter_table("distribution_events") as batch_op:
        batch_op.drop_constraint("fk_distribution_events_related_event_id", type_="foreignkey")
        batch_op.drop_column("related_event_id")
