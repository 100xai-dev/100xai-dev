"""blog scheduling and calendar tables

Revision ID: 20260607_0009
Revises: 20260602_0008
Create Date: 2026-06-07
"""

from alembic import op
import sqlalchemy as sa

revision = "20260607_0009"
down_revision = "20260602_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create blog_schedules table
    op.create_table(
        "blog_schedules",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("brand_id", sa.Uuid(), sa.ForeignKey("brands.id"), nullable=False),
        
        # Schedule information
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("slug", sa.String(500), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(50), nullable=False, default="UTC"),
        
        # Content reference
        sa.Column("blog_job_id", sa.Uuid(), sa.ForeignKey("blog_jobs.id"), nullable=True),
        sa.Column("blog_draft_id", sa.Uuid(), sa.ForeignKey("blog_drafts.id"), nullable=True),
        sa.Column("content_source", sa.String(), nullable=False, default="AI_GENERATED"),
        
        # Publishing configuration
        sa.Column("target_channels", sa.JSON(), nullable=False, default=list),
        sa.Column("channel_configs", sa.JSON(), nullable=False, default=dict),
        sa.Column("auto_publish", sa.Boolean(), nullable=False, default=True),
        
        # SEO & Keywords
        sa.Column("target_keyword", sa.String(200), nullable=True),
        sa.Column("meta_description", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False, default=list),
        sa.Column("categories", sa.JSON(), nullable=False, default=list),
        
        # Status tracking
        sa.Column("status", sa.String(), nullable=False, default="DRAFT"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_urls", sa.JSON(), nullable=False, default=dict),
        
        # Recurrence configuration
        sa.Column("recurrence_type", sa.String(), nullable=False, default="NONE"),
        sa.Column("recurrence_pattern", sa.JSON(), nullable=True),
        sa.Column("recurrence_end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("parent_schedule_id", sa.String(), sa.ForeignKey("blog_schedules.id"), nullable=True),
        
        # Error tracking
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, default=0),
        sa.Column("max_retries", sa.Integer(), nullable=False, default=3),
        
        # User tracking
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("last_modified_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create schedule_templates table
    op.create_table(
        "schedule_templates",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("brand_id", sa.Uuid(), sa.ForeignKey("brands.id"), nullable=False),
        
        # Template information
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        
        # Content configuration
        sa.Column("content_type", sa.String(50), nullable=True),
        sa.Column("keyword_pattern", sa.String(500), nullable=True),
        sa.Column("content_guidelines", sa.JSON(), nullable=False, default=dict),
        
        # Schedule pattern
        sa.Column("recurrence_type", sa.String(), nullable=False),
        sa.Column("recurrence_pattern", sa.JSON(), nullable=False),
        sa.Column("preferred_time", sa.Time(), nullable=True),
        sa.Column("timezone", sa.String(50), nullable=False, default="UTC"),
        
        # Auto-generation settings
        sa.Column("auto_generate", sa.Boolean(), nullable=False, default=False),
        sa.Column("generation_lead_time_hours", sa.Integer(), nullable=False, default=48),
        
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create content_calendars table
    op.create_table(
        "content_calendars",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("brand_id", sa.Uuid(), sa.ForeignKey("brands.id"), nullable=False),
        
        # Calendar period
        sa.Column("calendar_month", sa.Integer(), nullable=False),
        sa.Column("calendar_year", sa.Integer(), nullable=False),
        
        # Statistics
        sa.Column("total_scheduled", sa.Integer(), nullable=False, default=0),
        sa.Column("total_published", sa.Integer(), nullable=False, default=0),
        sa.Column("total_failed", sa.Integer(), nullable=False, default=0),
        
        # Content breakdown
        sa.Column("content_by_type", sa.JSON(), nullable=False, default=dict),
        sa.Column("content_by_channel", sa.JSON(), nullable=False, default=dict),
        
        # Performance metrics
        sa.Column("avg_engagement_score", sa.Integer(), nullable=True),
        sa.Column("top_performing_keywords", sa.JSON(), nullable=False, default=list),
        
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create publishing_queue table
    op.create_table(
        "publishing_queue",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("schedule_id", sa.String(), sa.ForeignKey("blog_schedules.id"), nullable=False),
        
        # Queue management
        sa.Column("priority", sa.Integer(), nullable=False, default=5),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_completed_at", sa.DateTime(timezone=True), nullable=True),
        
        # Target channel
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("channel_config", sa.JSON(), nullable=False, default=dict),
        
        # Status
        sa.Column("status", sa.String(), nullable=False, default="PENDING"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, default=0),
        sa.Column("last_error", sa.Text(), nullable=True),
        
        # Result
        sa.Column("published_url", sa.String(), nullable=True),
        sa.Column("external_id", sa.String(), nullable=True),
        
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create indexes for performance
    
    # blog_schedules indexes
    op.create_index("idx_schedule_brand_date", "blog_schedules", ["brand_id", "scheduled_at"])
    op.create_index("idx_schedule_status_date", "blog_schedules", ["status", "scheduled_at"])
    op.create_index("idx_schedule_org_id", "blog_schedules", ["org_id"])
    op.create_index("idx_schedule_blog_job_id", "blog_schedules", ["blog_job_id"])
    op.create_index("idx_schedule_blog_draft_id", "blog_schedules", ["blog_draft_id"])
    
    # content_calendars indexes
    op.create_index("idx_calendar_brand_period", "content_calendars", ["brand_id", "calendar_year", "calendar_month"])
    
    # publishing_queue indexes
    op.create_index("idx_queue_status_scheduled", "publishing_queue", ["status", "scheduled_for"])
    op.create_index("idx_queue_schedule_id", "publishing_queue", ["schedule_id"])
    
    # Add constraints
    op.create_unique_constraint("uq_brand_slug_date", "blog_schedules", ["brand_id", "slug", "scheduled_at"])
    op.create_unique_constraint("uq_brand_calendar_period", "content_calendars", ["brand_id", "calendar_year", "calendar_month"])
    op.create_unique_constraint("uq_schedule_channel", "publishing_queue", ["schedule_id", "channel"])
    
    # Add check constraints
    op.create_check_constraint("check_future_schedule", "blog_schedules", "scheduled_at > created_at")


def downgrade() -> None:
    op.drop_table("publishing_queue")
    op.drop_table("content_calendars") 
    op.drop_table("schedule_templates")
    op.drop_table("blog_schedules")