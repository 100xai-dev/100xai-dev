"""serp analysis pipeline tables

Revision ID: 20260602_0008
Revises: 20260601_0007
Create Date: 2026-06-02
"""

from alembic import op
import sqlalchemy as sa

revision = "20260602_0008"
down_revision = "20260601_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create serp_analyses table for Pipeline 2
    op.create_table(
        "serp_analyses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("brand_id", sa.Uuid(), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("keyword_id", sa.Uuid(), sa.ForeignKey("keywords.id", ondelete="CASCADE"), nullable=True),
        
        # SERP metadata
        sa.Column("keyword_text", sa.Text(), nullable=False),
        sa.Column("search_location", sa.String(), nullable=False, default="India"),
        sa.Column("search_language", sa.String(), nullable=False, default="English"),
        sa.Column("device_type", sa.String(), nullable=False, default="mobile"),
        sa.Column("serp_snapshot", sa.JSON(), nullable=True),
        
        # Analysis results summary
        sa.Column("total_results_analyzed", sa.Integer(), nullable=False, default=0),
        sa.Column("top_competitor_url", sa.Text(), nullable=True),
        sa.Column("avg_word_count", sa.Integer(), nullable=True),
        sa.Column("content_gap_score", sa.Float(), nullable=True),
        sa.Column("difficulty_analysis", sa.JSON(), nullable=True),
        
        # Analysis status
        sa.Column("status", sa.String(), nullable=False, default="PENDING"),
        sa.Column("error_message", sa.Text(), nullable=True),
        
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    
    # Create competitor_analyses table
    op.create_table(
        "competitor_analyses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("serp_analysis_id", sa.Uuid(), sa.ForeignKey("serp_analyses.id", ondelete="CASCADE"), nullable=False),
        
        # Competitor page info
        sa.Column("rank_position", sa.Integer(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("meta_description", sa.Text(), nullable=True),
        sa.Column("domain", sa.String(), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=True),
        
        # Crawled content
        sa.Column("raw_content", sa.Text(), nullable=True),
        sa.Column("content_summary", sa.Text(), nullable=True),
        
        # AI analysis results
        sa.Column("content_strength", sa.Float(), nullable=True),
        sa.Column("content_gaps", sa.JSON(), nullable=True),
        sa.Column("competitive_advantage", sa.Text(), nullable=True),
        sa.Column("target_audience", sa.Text(), nullable=True),
        sa.Column("content_tone", sa.String(), nullable=True),
        sa.Column("key_topics", sa.JSON(), nullable=True),
        sa.Column("internal_links_count", sa.Integer(), nullable=True),
        sa.Column("external_links_count", sa.Integer(), nullable=True),
        
        # Technical metrics
        sa.Column("load_time_ms", sa.Integer(), nullable=True),
        sa.Column("mobile_friendly", sa.Boolean(), nullable=True),
        sa.Column("has_schema_markup", sa.Boolean(), nullable=True),
        
        # Quality metrics
        sa.Column("crawl_success", sa.Boolean(), nullable=False, default=False),
        sa.Column("analysis_success", sa.Boolean(), nullable=False, default=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("crawled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True),
    )
    
    # Add indexes for performance
    op.create_index("idx_serp_analyses_job_id", "serp_analyses", ["job_id"])
    op.create_index("idx_serp_analyses_brand_id", "serp_analyses", ["brand_id"])
    op.create_index("idx_serp_analyses_keyword_id", "serp_analyses", ["keyword_id"])
    op.create_index("idx_serp_analyses_keyword_text", "serp_analyses", ["keyword_text"])
    op.create_index("idx_serp_analyses_status", "serp_analyses", ["status"])
    
    op.create_index("idx_competitor_analyses_serp_analysis_id", "competitor_analyses", ["serp_analysis_id"])
    op.create_index("idx_competitor_analyses_rank_position", "competitor_analyses", ["rank_position"])
    op.create_index("idx_competitor_analyses_domain", "competitor_analyses", ["domain"])
    op.create_index("idx_competitor_analyses_content_strength", "competitor_analyses", ["content_strength"])


def downgrade() -> None:
    op.drop_table("competitor_analyses")
    op.drop_table("serp_analyses")