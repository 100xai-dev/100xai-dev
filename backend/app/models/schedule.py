"""Blog scheduling models for content calendar management."""

from datetime import datetime
from enum import Enum
from sqlalchemy import (
    JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, Time,
    UniqueConstraint, Index, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, utcnow, uuid_str


class ScheduleStatus(str, Enum):
    """Status of a scheduled post."""
    DRAFT = "DRAFT"                    # Content being created/edited
    SCHEDULED = "SCHEDULED"            # Scheduled for future publishing
    PUBLISHING = "PUBLISHING"          # Currently being published
    PUBLISHED = "PUBLISHED"            # Successfully published
    FAILED = "FAILED"                  # Publishing failed
    CANCELLED = "CANCELLED"            # Cancelled by user
    PAUSED = "PAUSED"                  # Temporarily paused


class RecurrenceType(str, Enum):
    """Types of recurring schedules."""
    NONE = "NONE"                      # One-time post
    DAILY = "DAILY"                    # Every day
    WEEKLY = "WEEKLY"                  # Weekly on specific days
    BIWEEKLY = "BIWEEKLY"             # Every two weeks
    MONTHLY = "MONTHLY"                # Monthly on specific date
    CUSTOM = "CUSTOM"                   # Custom cron expression


class ContentSource(str, Enum):
    """Source of the blog content."""
    AI_GENERATED = "AI_GENERATED"      # Generated via Pipeline 3
    MANUAL = "MANUAL"                  # User-written content
    IMPORTED = "IMPORTED"              # Imported from external source
    CURATED = "CURATED"                # Curated/edited AI content


class BlogSchedule(Base, TimestampMixin):
    """Main scheduling table for blog posts."""
    __tablename__ = "blog_schedules"
    
    # Primary identifiers
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"), nullable=False)
    
    # Schedule information
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str | None] = mapped_column(String(500))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    
    # Content reference
    blog_job_id: Mapped[str | None] = mapped_column(ForeignKey("blog_jobs.id"))
    blog_draft_id: Mapped[str | None] = mapped_column(ForeignKey("blog_drafts.id"))
    content_source: Mapped[str] = mapped_column(String, default=ContentSource.AI_GENERATED)
    
    # Publishing configuration
    target_channels: Mapped[list[str]] = mapped_column(JSON, default=list)  # ["wordpress", "shopify"]
    channel_configs: Mapped[dict] = mapped_column(JSON, default=dict)  # Channel-specific settings
    auto_publish: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # SEO & Keywords
    target_keyword: Mapped[str | None] = mapped_column(String(200))
    meta_description: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    categories: Mapped[list[str]] = mapped_column(JSON, default=list)
    
    # Status tracking
    status: Mapped[str] = mapped_column(String, default=ScheduleStatus.DRAFT, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_urls: Mapped[dict] = mapped_column(JSON, default=dict)  # {"wordpress": "url", "shopify": "url"}
    
    # Recurrence configuration
    recurrence_type: Mapped[str] = mapped_column(String, default=RecurrenceType.NONE)
    recurrence_pattern: Mapped[dict | None] = mapped_column(JSON)  # Stores pattern details
    recurrence_end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    parent_schedule_id: Mapped[str | None] = mapped_column(ForeignKey("blog_schedules.id"))
    
    # Error tracking
    last_error: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    
    # User tracking
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    last_modified_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    brand: Mapped["Brand"] = relationship("Brand", back_populates="schedules")
    blog_job: Mapped["BlogJob | None"] = relationship("BlogJob", back_populates="schedules")
    blog_draft: Mapped["BlogDraft | None"] = relationship("BlogDraft", back_populates="schedules")
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_schedule_brand_date", "brand_id", "scheduled_at"),
        Index("idx_schedule_status_date", "status", "scheduled_at"),
        UniqueConstraint("brand_id", "slug", "scheduled_at", name="uq_brand_slug_date"),
        CheckConstraint("scheduled_at > created_at", name="check_future_schedule"),
    )


class ScheduleTemplate(Base, TimestampMixin):
    """Templates for recurring content schedules."""
    __tablename__ = "schedule_templates"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"), nullable=False)
    
    # Template information
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Content configuration
    content_type: Mapped[str] = mapped_column(String(50))  # "how-to", "listicle", "news", etc.
    keyword_pattern: Mapped[str | None] = mapped_column(String(500))  # Pattern for keyword selection
    content_guidelines: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Schedule pattern
    recurrence_type: Mapped[str] = mapped_column(String, nullable=False)
    recurrence_pattern: Mapped[dict] = mapped_column(JSON, nullable=False)
    preferred_time: Mapped[datetime | None] = mapped_column(Time)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    
    # Auto-generation settings
    auto_generate: Mapped[bool] = mapped_column(Boolean, default=False)
    generation_lead_time_hours: Mapped[int] = mapped_column(Integer, default=48)
    
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)


class ContentCalendar(Base, TimestampMixin):
    """Aggregated calendar view for content planning."""
    __tablename__ = "content_calendars"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"), nullable=False)
    
    # Calendar period
    calendar_month: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-12
    calendar_year: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Statistics
    total_scheduled: Mapped[int] = mapped_column(Integer, default=0)
    total_published: Mapped[int] = mapped_column(Integer, default=0)
    total_failed: Mapped[int] = mapped_column(Integer, default=0)
    
    # Content breakdown
    content_by_type: Mapped[dict] = mapped_column(JSON, default=dict)
    content_by_channel: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Performance metrics
    avg_engagement_score: Mapped[float | None] = mapped_column(Integer)
    top_performing_keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    
    __table_args__ = (
        UniqueConstraint("brand_id", "calendar_year", "calendar_month", name="uq_brand_calendar_period"),
        Index("idx_calendar_brand_period", "brand_id", "calendar_year", "calendar_month"),
    )


class PublishingQueue(Base, TimestampMixin):
    """Queue for managing publishing tasks."""
    __tablename__ = "publishing_queue"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    schedule_id: Mapped[str] = mapped_column(ForeignKey("blog_schedules.id"), nullable=False)
    
    # Queue management
    priority: Mapped[int] = mapped_column(Integer, default=5)  # 1-10, higher = more priority
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Target channel
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    channel_config: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Status
    status: Mapped[str] = mapped_column(String, default="PENDING", index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    
    # Result
    published_url: Mapped[str | None] = mapped_column(String)
    external_id: Mapped[str | None] = mapped_column(String)  # WordPress post ID, etc.
    
    schedule: Mapped["BlogSchedule"] = relationship("BlogSchedule")
    
    __table_args__ = (
        Index("idx_queue_status_scheduled", "status", "scheduled_for"),
        UniqueConstraint("schedule_id", "channel", name="uq_schedule_channel"),
    )