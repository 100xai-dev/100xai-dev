"""Keyword research models for Pipeline 1."""

from datetime import datetime
from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, uuid_str


class Keyword(Base):
    """Keywords discovered and analyzed by Pipeline 1 (Keyword Research)."""
    __tablename__ = "keywords"

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
    
    # Keyword data
    related_keyword: Mapped[str] = mapped_column(Text, nullable=False)
    primary_keyword: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String, nullable=False)  # 'related_keywords', 'suggestions', etc.
    
    # SEO metrics (nullable - will be populated by enrichment step)
    search_volume: Mapped[int | None] = mapped_column(Integer)
    keyword_difficulty: Mapped[int | None] = mapped_column(Integer)
    cpc: Mapped[float | None] = mapped_column(Float)
    competition: Mapped[float | None] = mapped_column(Float)
    search_intent: Mapped[str | None] = mapped_column(String)
    
    # Computed score (40% volume, 40% inverse difficulty, 20% CPC)
    score: Mapped[float | None] = mapped_column(Float)
    
    # Add created_at timestamp manually since not using TimestampMixin  
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)

    # Relationships (if needed for future queries)
    # job: Mapped["Job"] = relationship()
    # brand: Mapped["Brand"] = relationship()