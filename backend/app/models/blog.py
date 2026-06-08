from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, utcnow, uuid_str

# ---------------------------------------------------------------------------
# Status constants
# ---------------------------------------------------------------------------

BLOG_STATUS_NEW = "NEW"
BLOG_STATUS_RESEARCHING = "RESEARCHING"
BLOG_STATUS_BRIEFING = "BRIEFING"
BLOG_STATUS_PENDING_BRIEF_REVIEW = "PENDING_BRIEF_REVIEW"
BLOG_STATUS_WRITING = "WRITING"
BLOG_STATUS_PENDING_REVIEW = "PENDING_REVIEW"
BLOG_STATUS_PUBLISHING = "PUBLISHING"
BLOG_STATUS_PUBLISHED = "PUBLISHED"
BLOG_STATUS_FAILED = "FAILED"
BLOG_STATUS_REJECTED = "REJECTED"

ACTIVE_BLOG_STATUSES = {
    BLOG_STATUS_RESEARCHING,
    BLOG_STATUS_BRIEFING,
    BLOG_STATUS_WRITING,
    BLOG_STATUS_PUBLISHING,
}


class BlogJob(Base, TimestampMixin):
    __tablename__ = "blog_jobs"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_str)
    org_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("organizations.id"), nullable=False)
    brand_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False)
    created_by: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("users.id"), nullable=False)

    keyword: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default=BLOG_STATUS_NEW)
    error_message: Mapped[str | None] = mapped_column(Text)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    brief: Mapped[BlogBrief | None] = relationship(back_populates="job", cascade="all, delete-orphan", uselist=False)
    sections: Mapped[list[BlogSection]] = relationship(back_populates="job", cascade="all, delete-orphan", order_by="BlogSection.section_index")
    draft: Mapped[BlogDraft | None] = relationship(back_populates="job", cascade="all, delete-orphan", uselist=False)
    schedules: Mapped[list["BlogSchedule"]] = relationship("BlogSchedule", back_populates="blog_job")


class BlogBrief(Base, TimestampMixin):
    __tablename__ = "blog_briefs"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_str)
    job_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("blog_jobs.id", ondelete="CASCADE"), nullable=False, unique=True)

    selected_title: Mapped[str] = mapped_column(String, nullable=False)
    title_options: Mapped[list[str]] = mapped_column(JSON, default=list)
    meta_description: Mapped[str] = mapped_column(Text, nullable=False)
    search_intent: Mapped[str] = mapped_column(String, nullable=False)
    target_word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1500)
    target_audience: Mapped[str | None] = mapped_column(Text)
    keyword_variants: Mapped[list[str]] = mapped_column(JSON, default=list)
    outline: Mapped[list[dict]] = mapped_column(JSON, default=list)
    aeo: Mapped[dict] = mapped_column(JSON, default=dict)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    serp_snapshot: Mapped[dict | None] = mapped_column(JSON)
    approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(Uuid(as_uuid=False))

    job: Mapped[BlogJob] = relationship(back_populates="brief")


class BlogSection(Base, TimestampMixin):
    __tablename__ = "blog_sections"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_str)
    job_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("blog_jobs.id", ondelete="CASCADE"), nullable=False)

    section_index: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[str] = mapped_column(String, nullable=False)
    heading_type: Mapped[str] = mapped_column(String, nullable=False, default="h2")
    key_points: Mapped[list[str]] = mapped_column(JSON, default=list)
    estimated_words: Mapped[int] = mapped_column(Integer, default=200)
    content_html: Mapped[str | None] = mapped_column(Text)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, nullable=False, default="PENDING")

    job: Mapped[BlogJob] = relationship(back_populates="sections")


class BlogDraft(Base, TimestampMixin):
    __tablename__ = "blog_drafts"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_str)
    job_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("blog_jobs.id", ondelete="CASCADE"), nullable=False, unique=True)

    title: Mapped[str] = mapped_column(String, nullable=False)
    meta_description: Mapped[str] = mapped_column(Text, nullable=False)
    html_content: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    seo_score: Mapped[int] = mapped_column(Integer, default=0)
    aeo_score: Mapped[int] = mapped_column(Integer, default=0)
    virality_score: Mapped[int] = mapped_column(Integer, default=0)
    featured_image_url: Mapped[str | None] = mapped_column(String)
    approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(Uuid(as_uuid=False))

    job: Mapped[BlogJob] = relationship(back_populates="draft")
    schedules: Mapped[list["BlogSchedule"]] = relationship("BlogSchedule", back_populates="blog_draft")
