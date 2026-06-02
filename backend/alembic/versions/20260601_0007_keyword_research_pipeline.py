"""keyword research pipeline tables

Revision ID: 20260601_0007
Revises: 20260601_0006
Create Date: 2026-06-01
"""

from alembic import op
import sqlalchemy as sa

revision = "20260601_0007"
down_revision = "20260601_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create keywords table for Pipeline 1
    op.create_table(
        "keywords",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("brand_id", sa.Uuid(), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("related_keyword", sa.Text(), nullable=False),
        sa.Column("primary_keyword", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),  # 'related_keywords' | 'suggestions' | 'ideas' | 'autocomplete' | 'sub_topics'
        sa.Column("search_volume", sa.Integer(), nullable=True),
        sa.Column("keyword_difficulty", sa.Integer(), nullable=True),
        sa.Column("cpc", sa.Float(), nullable=True),
        sa.Column("competition", sa.Float(), nullable=True),
        sa.Column("search_intent", sa.String(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Add indexes
    op.create_index("idx_keywords_job_id", "keywords", ["job_id"])
    op.create_index("idx_keywords_brand_id", "keywords", ["brand_id"])
    op.create_index("idx_keywords_score", "keywords", ["score"])
    op.create_index("idx_keywords_related_keyword", "keywords", ["related_keyword"])
    
    # Ensure existing jobs have stage values (column already exists)
    op.execute("UPDATE jobs SET stage = 'NEW' WHERE stage IS NULL OR stage = ''")


def downgrade() -> None:
    op.drop_table("keywords")
    # Note: Not dropping stage column from jobs as it might be used by other features