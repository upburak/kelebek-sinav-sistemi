"""Create draft exam organizations and course/student selections.

Revision ID: 0006_exam_organizations
Revises: 0005_school_profile
Create Date: 2026-11-07
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_exam_organizations"
down_revision = "0005_school_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "courses",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("normalized_name", sa.String(length=120), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_name"),
    )
    op.create_table(
        "exam_organizations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("academic_year_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("exam_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'completed')", name="ck_exam_organization_status"
        ),
        sa.ForeignKeyConstraint(["academic_year_id"], ["academic_years.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_exam_organizations_year_date",
        "exam_organizations",
        ["academic_year_id", "exam_date"],
    )
    op.create_table(
        "exam_courses",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("course_id", sa.String(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["exam_organizations.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "course_id"),
    )
    op.create_table(
        "exam_participants",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("enrollment_id", sa.String(), nullable=False),
        sa.Column("school_number", sa.String(length=64), nullable=False),
        sa.Column("first_name", sa.String(length=120), nullable=False),
        sa.Column("last_name", sa.String(length=120), nullable=False),
        sa.Column("class_level", sa.String(length=32), nullable=False),
        sa.Column("section", sa.String(length=32), nullable=False),
        sa.Column("area", sa.String(length=120), nullable=True),
        sa.ForeignKeyConstraint(
            ["enrollment_id"], ["student_year_enrollments.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["exam_organizations.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "enrollment_id"),
    )
    op.create_table(
        "exam_course_participants",
        sa.Column("exam_course_id", sa.String(), nullable=False),
        sa.Column("participant_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["exam_course_id"], ["exam_courses.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["participant_id"], ["exam_participants.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("exam_course_id", "participant_id"),
    )


def downgrade() -> None:
    op.drop_table("exam_course_participants")
    op.drop_table("exam_participants")
    op.drop_table("exam_courses")
    op.drop_index("ix_exam_organizations_year_date", table_name="exam_organizations")
    op.drop_table("exam_organizations")
    op.drop_table("courses")
