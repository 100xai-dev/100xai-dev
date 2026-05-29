"""tenancy hardening, indexes, per-org user email

Revision ID: 20260528_0003
Revises: 20260528_0002
Create Date: 2026-05-28
"""

from alembic import op
import sqlalchemy as sa

revision = "20260528_0003"
down_revision = "20260528_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------------------------------------------
    # jobs.org_id: backfill from brand.org_id, then enforce NOT NULL
    # ---------------------------------------------------------------
    op.execute(
        """
        UPDATE jobs
           SET org_id = brands.org_id
          FROM brands
         WHERE jobs.org_id IS NULL
           AND jobs.brand_id = brands.id
        """
    )
    op.alter_column("jobs", "org_id", existing_type=sa.Uuid(), nullable=False)

    # ---------------------------------------------------------------
    # Per-org unique email instead of global unique
    # The original migration created the column with unique=True, so
    # Postgres named the constraint `users_email_key`.
    # ---------------------------------------------------------------
    op.drop_constraint("users_email_key", "users", type_="unique")
    op.create_unique_constraint("uq_users_org_email", "users", ["org_id", "email"])

    # ---------------------------------------------------------------
    # Missing indexes for hot read paths
    # ---------------------------------------------------------------
    op.create_index("idx_sources_brand_id", "brand_knowledge_sources", ["brand_id"])
    op.create_index(
        "idx_chunks_brand_source", "brand_knowledge_chunks", ["brand_id", "source_id"]
    )
    op.create_index(
        "idx_integrations_brand_id", "integration_accounts", ["brand_id"]
    )
    op.create_index("idx_jobs_brand_id", "jobs", ["brand_id"])
    op.create_index("idx_audit_org_created", "audit_logs", ["org_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_audit_org_created", table_name="audit_logs")
    op.drop_index("idx_jobs_brand_id", table_name="jobs")
    op.drop_index("idx_integrations_brand_id", table_name="integration_accounts")
    op.drop_index("idx_chunks_brand_source", table_name="brand_knowledge_chunks")
    op.drop_index("idx_sources_brand_id", table_name="brand_knowledge_sources")

    op.drop_constraint("uq_users_org_email", "users", type_="unique")
    op.create_unique_constraint("users_email_key", "users", ["email"])

    op.alter_column("jobs", "org_id", existing_type=sa.Uuid(), nullable=True)
