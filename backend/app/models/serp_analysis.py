"""SERP analysis models for Pipeline 2."""

from datetime import datetime
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, uuid_str


class SerpAnalysis(Base):
    """SERP analysis results for Pipeline 2 (SERP Analysis)."""
    __tablename__ = "serp_analyses"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_str)
    job_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), 
        ForeignKey("jobs.id", ondelete="CASCADE"), 
        nullable=False
    )
    brand_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), 
        ForeignKey("brands.id", ondelete="CASCADE"), 
        nullable=False
    )
    keyword_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False), 
        ForeignKey("keywords.id", ondelete="CASCADE"), 
        nullable=True  # Nullable for batch analyses
    )
    
    # SERP metadata
    keyword_text: Mapped[str] = mapped_column(Text, nullable=False)
    search_location: Mapped[str] = mapped_column(String, default="India", nullable=False)
    search_language: Mapped[str] = mapped_column(String, default="English", nullable=False)
    device_type: Mapped[str] = mapped_column(String, default="mobile", nullable=False)
    serp_snapshot: Mapped[dict | None] = mapped_column(JSON)  # Full SERP data
    
    # Analysis results summary
    total_results_analyzed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    top_competitor_url: Mapped[str | None] = mapped_column(Text)
    avg_word_count: Mapped[int | None] = mapped_column(Integer)
    content_gap_score: Mapped[float | None] = mapped_column(Float)  # 0-1 scale
    difficulty_analysis: Mapped[dict | None] = mapped_column(JSON)
    
    # Analysis status
    status: Mapped[str] = mapped_column(String, default="PENDING", nullable=False)  # PENDING, PROCESSING, COMPLETED, FAILED
    error_message: Mapped[str | None] = mapped_column(Text)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    competitors: Mapped[list["CompetitorAnalysis"]] = relationship(
        back_populates="serp_analysis", 
        cascade="all, delete-orphan",
        order_by="CompetitorAnalysis.rank_position"
    )


class CompetitorAnalysis(Base):
    """Individual competitor page analysis."""
    __tablename__ = "competitor_analyses"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_str)
    serp_analysis_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), 
        ForeignKey("serp_analyses.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    # Competitor page info
    rank_position: Mapped[int] = mapped_column(Integer, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    meta_description: Mapped[str | None] = mapped_column(Text)
    domain: Mapped[str | None] = mapped_column(String)
    word_count: Mapped[int | None] = mapped_column(Integer)
    
    # Crawled content
    raw_content: Mapped[str | None] = mapped_column(Text)  # Markdown content
    content_summary: Mapped[str | None] = mapped_column(Text)
    
    # AI analysis results
    content_strength: Mapped[float | None] = mapped_column(Float)  # 0-1 scale
    content_gaps: Mapped[list | None] = mapped_column(JSON)  # ["missing topic 1", "missing topic 2"]
    competitive_advantage: Mapped[str | None] = mapped_column(Text)
    target_audience: Mapped[str | None] = mapped_column(Text)
    content_tone: Mapped[str | None] = mapped_column(String)
    key_topics: Mapped[list | None] = mapped_column(JSON)  # ["topic1", "topic2"]
    internal_links_count: Mapped[int | None] = mapped_column(Integer)
    external_links_count: Mapped[int | None] = mapped_column(Integer)
    
    # Technical metrics
    load_time_ms: Mapped[int | None] = mapped_column(Integer)
    mobile_friendly: Mapped[bool | None] = mapped_column(Boolean)
    has_schema_markup: Mapped[bool | None] = mapped_column(Boolean)
    
    # Quality metrics
    crawl_success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    analysis_success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    serp_analysis: Mapped[SerpAnalysis] = relationship(back_populates="competitors")