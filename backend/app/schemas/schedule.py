"""Schedule-related Pydantic schemas."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class ScheduleStatus(str, Enum):
    """Status of a scheduled post."""
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    PUBLISHING = "PUBLISHING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PAUSED = "PAUSED"


class RecurrenceType(str, Enum):
    """Types of recurring schedules."""
    NONE = "NONE"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    BIWEEKLY = "BIWEEKLY"
    MONTHLY = "MONTHLY"
    CUSTOM = "CUSTOM"


class ContentSource(str, Enum):
    """Source of the blog content."""
    AI_GENERATED = "AI_GENERATED"
    MANUAL = "MANUAL"
    IMPORTED = "IMPORTED"
    CURATED = "CURATED"


# --- Request Schemas ---

class CreateScheduleRequest(BaseModel):
    """Request to create a new schedule."""
    brand_id: str
    title: str = Field(..., min_length=1, max_length=500)
    scheduled_at: datetime
    target_keyword: Optional[str] = Field(None, max_length=200)
    blog_job_id: Optional[str] = None
    blog_draft_id: Optional[str] = None
    target_channels: List[str] = Field(default_factory=list)
    timezone_str: str = Field("UTC", alias="timezone")
    meta_description: Optional[str] = None


class BulkScheduleItem(BaseModel):
    """One day's scheduled blog: a date plus the keyword/topic to generate."""
    date: str = Field(..., description="Calendar date, YYYY-MM-DD")
    keyword: str = Field(..., min_length=1, max_length=200)


class BulkScheduleRequest(BaseModel):
    """Schedule blog content across one or more days in a single request."""
    items: List[BulkScheduleItem] = Field(..., min_length=1)
    time: str = Field("09:00", description="Publish time-of-day for all items, HH:MM (24h)")
    timezone_str: str = Field("UTC", alias="timezone")
    channels: List[str] = Field(default_factory=lambda: ["wordpress"])


# --- Response Schemas for Publishing Monitoring ---

class ChannelStatsResponse(BaseModel):
    """Channel-specific publishing statistics."""
    channel: str
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    success_rate: float


class RecentActivityResponse(BaseModel):
    """Recent publishing activity item."""
    id: str
    title: str
    status: str
    published_at: Optional[datetime]
    channels: List[str]
    published_urls: Dict[str, str]


class PublishingStatsResponse(BaseModel):
    """Publishing statistics response."""
    brand_id: str
    period_days: int
    total_schedules: int
    published_count: int
    failed_count: int
    pending_count: int
    success_rate: float
    channel_stats: List[ChannelStatsResponse]
    recent_activity: List[RecentActivityResponse]


class ScheduleInfoResponse(BaseModel):
    """Basic schedule information."""
    title: str
    status: str
    slug: Optional[str] = None


class PublishingQueueResponse(BaseModel):
    """Publishing queue entry response."""
    id: str
    schedule_id: str
    channel: str
    status: str
    scheduled_for: datetime
    processing_started_at: Optional[datetime]
    processing_completed_at: Optional[datetime]
    attempt_count: int
    last_error: Optional[str]
    published_url: Optional[str]
    external_id: Optional[str]
    schedule: ScheduleInfoResponse


class FailedPublishingResponse(BaseModel):
    """Failed publishing job response."""
    id: str
    schedule_id: str
    channel: str
    failed_at: Optional[datetime]
    attempt_count: int
    last_error: Optional[str]
    can_retry: bool
    schedule: ScheduleInfoResponse


class CreateScheduleRequest(BaseModel):
    """Request to create a new schedule."""
    brand_id: str
    title: str = Field(..., min_length=1, max_length=500)
    scheduled_at: datetime
    target_keyword: Optional[str] = Field(None, max_length=200)
    blog_job_id: Optional[str] = None
    blog_draft_id: Optional[str] = None
    target_channels: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    auto_publish: bool = True
    
    @validator('scheduled_at')
    def scheduled_at_must_be_future(cls, v):
        if v <= datetime.now():
            raise ValueError('Scheduled time must be in the future')
        return v
    
    @validator('target_channels')
    def validate_channels(cls, v):
        valid_channels = {'wordpress', 'shopify', 'webhook', 'email'}
        invalid = set(v) - valid_channels
        if invalid:
            raise ValueError(f'Invalid channels: {invalid}. Valid: {valid_channels}')
        return v


class UpdateScheduleRequest(BaseModel):
    """Request to update a schedule."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    scheduled_at: Optional[datetime] = None
    target_channels: Optional[List[str]] = None
    auto_publish: Optional[bool] = None
    target_keyword: Optional[str] = Field(None, max_length=200)
    meta_description: Optional[str] = None
    tags: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    
    @validator('scheduled_at')
    def scheduled_at_must_be_future(cls, v):
        if v and v <= datetime.now():
            raise ValueError('Scheduled time must be in the future')
        return v


class CreateTemplateRequest(BaseModel):
    """Request to create a schedule template."""
    brand_id: str
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    content_type: Optional[str] = Field(None, max_length=50)
    keyword_pattern: Optional[str] = Field(None, max_length=500)
    content_guidelines: Dict[str, Any] = Field(default_factory=dict)
    recurrence_type: RecurrenceType
    recurrence_pattern: Dict[str, Any] = Field(...)
    preferred_time: Optional[str] = None  # HH:MM format
    timezone: str = "UTC"
    auto_generate: bool = False
    generation_lead_time_hours: int = Field(48, ge=1, le=168)  # 1 hour to 1 week


# --- Response Schemas ---

class ScheduleResponse(BaseModel):
    """Basic schedule information response."""
    id: str
    title: str
    slug: Optional[str]
    scheduled_at: datetime
    timezone: str
    brand_id: str
    blog_job_id: Optional[str]
    blog_draft_id: Optional[str]
    content_source: ContentSource
    target_channels: List[str]
    auto_publish: bool
    target_keyword: Optional[str]
    meta_description: Optional[str]
    tags: List[str]
    categories: List[str]
    status: ScheduleStatus
    published_at: Optional[datetime]
    published_urls: Dict[str, str]
    recurrence_type: RecurrenceType
    last_error: Optional[str]
    retry_count: int
    created_at: datetime
    updated_at: datetime


class ScheduleSummary(BaseModel):
    """Summary schedule information for lists."""
    id: str
    title: str
    scheduled_at: datetime
    status: ScheduleStatus
    target_keyword: Optional[str]
    target_channels: List[str]
    content_source: ContentSource


class CalendarResponse(BaseModel):
    """Calendar view response."""
    schedules: List[ScheduleSummary]
    month: int
    year: int
    total_scheduled: int
    total_published: int
    total_failed: int


class PublishingQueueItem(BaseModel):
    """Publishing queue item response."""
    id: str
    schedule_id: str
    channel: str
    scheduled_for: datetime
    status: str
    attempt_count: int
    last_error: Optional[str]
    published_url: Optional[str]
    external_id: Optional[str]
    processing_started_at: Optional[datetime]
    processing_completed_at: Optional[datetime]


class TemplateResponse(BaseModel):
    """Schedule template response."""
    id: str
    brand_id: str
    name: str
    description: Optional[str]
    is_active: bool
    content_type: Optional[str]
    keyword_pattern: Optional[str]
    content_guidelines: Dict[str, Any]
    recurrence_type: RecurrenceType
    recurrence_pattern: Dict[str, Any]
    preferred_time: Optional[str]
    timezone: str
    auto_generate: bool
    generation_lead_time_hours: int
    created_at: datetime
    updated_at: datetime


# --- Statistics Schemas ---

class ScheduleStats(BaseModel):
    """Schedule statistics."""
    total_scheduled: int
    total_published: int
    total_failed: int
    upcoming_this_week: int
    overdue: int
    channels_breakdown: Dict[str, int]
    status_breakdown: Dict[str, int]


class ContentCalendarStats(BaseModel):
    """Content calendar statistics."""
    month: int
    year: int
    total_scheduled: int
    total_published: int
    total_failed: int
    content_by_type: Dict[str, int]
    content_by_channel: Dict[str, int]
    top_performing_keywords: List[str]
    avg_engagement_score: Optional[float]