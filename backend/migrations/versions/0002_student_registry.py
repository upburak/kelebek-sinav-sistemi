"""Add student identity and year enrollment tables.

Revision ID: 0002_student_registry
Revises: 0001_academic_years
Create Date: 2026-11-06
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_student_registry"
down_revision = "0001_academic_years"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "students",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "student_year_enrollments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("academic_year_id", sa.String(), nullable=False),
        sa.Column("student_id", sa.String(), nullable=False),
        sa.Column("school_number", sa.String(length=64), nullable=False),
        sa.Column("first_name", sa.String(length=120), nullable=False),
        sa.Column("last_name", sa.String(length=120), nullable=False),
        sa.Column("class_level", sa.String(length=32), nullable=False),
        sa.Column("section", sa.String(length=32), nullable=False),
        sa.Column("area", sa.String(length=120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["academic_year_id"], ["academic_years.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_active_enrollment_school_number",
        "student_year_enrollments",
        ["academic_year_id", "school_number"],
        unique=True,
        sqlite_where=sa.text("is_active = 1"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_active_enrollment_school_number", table_name="student_year_enrollments"
    )
    op.drop_table("student_year_enrollments")
    op.drop_table("students")
