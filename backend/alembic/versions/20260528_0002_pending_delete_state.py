"""add pending delete state and job org scope

Revision ID: 20260528_0002
Revises: 20260527_0001
Create Date: 2026-05-28
"""

from alembic import op
import sqlalchemy as sa

revision = "20260528_0002"
down_revision = "20260527_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_brands_status", "brands", type_="check")
    op.create_check_constraint(
        "ck_brands_status",
        "brands",
        "status IN ('DRAFT', 'CRAWLING', 'EXTRACTING', 'INGESTING', 'PENDING_REVIEW', 'READY', 'FAILED', 'PENDING_DELETE')",
    )
    op.add_column("jobs", sa.Column("org_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_jobs_org_id", "jobs", "organizations", ["org_id"], ["id"])
    op.create_index("idx_jobs_org_status", "jobs", ["org_id", "status"])


def downgrade() -> None:
    op.drop_index("idx_jobs_org_status", table_name="jobs")
    op.drop_constraint("fk_jobs_org_id", "jobs", type_="foreignkey")
    op.drop_column("jobs", "org_id")
    op.drop_constraint("ck_brands_status", "brands", type_="check")
    op.create_check_constraint(
        "ck_brands_status",
        "brands",
        "status IN ('DRAFT', 'CRAWLING', 'EXTRACTING', 'INGESTING', 'PENDING_REVIEW', 'READY', 'FAILED')",
    )

