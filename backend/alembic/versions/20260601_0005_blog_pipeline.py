"""blog pipeline tables

Revision ID: 20260601_0005
Revises: 20260601_0004
Create Date: 2026-06-01
"""

from alembic import op
import sqlalchemy as sa

revision = "20260601_0005"
down_revision = "20260601_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "blog_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("org_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("brand_id", sa.Uuid(), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("keyword", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="NEW"),
        sa.Column("error_message", sa.Text()),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_blog_jobs_brand_id", "blog_jobs", ["brand_id"])
    op.create_index("ix_blog_jobs_org_id", "blog_jobs", ["org_id"])

    op.create_table(
        "blog_briefs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("blog_jobs.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("selected_title", sa.String(), nullable=False),
        sa.Column("title_options", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("meta_description", sa.Text(), nullable=False),
        sa.Column("search_intent", sa.String(), nullable=False),
        sa.Column("target_word_count", sa.Integer(), nullable=False, server_default="1500"),
        sa.Column("target_audience", sa.Text()),
        sa.Column("keyword_variants", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("outline", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("aeo", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("serp_snapshot", sa.JSON()),
        sa.Column("approved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("approved_by", sa.Uuid()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "blog_sections",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("blog_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section_index", sa.Integer(), nullable=False),
        sa.Column("heading", sa.String(), nullable=False),
        sa.Column("heading_type", sa.String(), nullable=False, server_default="h2"),
        sa.Column("key_points", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("estimated_words", sa.Integer(), server_default="200"),
        sa.Column("content_html", sa.Text()),
        sa.Column("word_count", sa.Integer(), server_default="0"),
        sa.Column("status", sa.String(), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_blog_sections_job_id", "blog_sections", ["job_id"])

    op.create_table(
        "blog_drafts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("blog_jobs.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("meta_description", sa.Text(), nullable=False),
        sa.Column("html_content", sa.Text(), nullable=False),
        sa.Column("word_count", sa.Integer(), server_default="0"),
        sa.Column("seo_score", sa.Integer(), server_default="0"),
        sa.Column("aeo_score", sa.Integer(), server_default="0"),
        sa.Column("virality_score", sa.Integer(), server_default="0"),
        sa.Column("featured_image_url", sa.String()),
        sa.Column("approved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("approved_by", sa.Uuid()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("blog_drafts")
    op.drop_index("ix_blog_sections_job_id", "blog_sections")
    op.drop_table("blog_sections")
    op.drop_table("blog_briefs")
    op.drop_index("ix_blog_jobs_org_id", "blog_jobs")
    op.drop_index("ix_blog_jobs_brand_id", "blog_jobs")
    op.drop_table("blog_jobs")
