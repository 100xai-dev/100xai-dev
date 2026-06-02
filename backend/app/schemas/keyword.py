"""Schemas for keyword research endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class KeywordResearchRequest(BaseModel):
    """Request to start keyword research for a brand."""
    seed_keyword: str = Field(..., min_length=1, max_length=200, description="The primary keyword to research")
    

class KeywordResearchResponse(BaseModel):
    """Response when starting keyword research."""
    job_id: str
    brand_id: str
    seed_keyword: str
    status: str
    message: str


class KeywordOut(BaseModel):
    """Individual keyword response."""
    id: str
    related_keyword: str
    primary_keyword: str
    source_type: str
    search_volume: Optional[int] = None
    keyword_difficulty: Optional[int] = None
    cpc: Optional[float] = None
    competition: Optional[float] = None
    search_intent: Optional[str] = None
    score: Optional[float] = None
    created_at: datetime


class KeywordListResponse(BaseModel):
    """Response for keyword listing."""
    keywords: list[KeywordOut]
    total: int
    brand_id: str
    latest_job_id: Optional[str] = None
    research_status: str  # 'never_run', 'processing', 'completed', 'failed'


class KeywordStatsResponse(BaseModel):
    """Keywords research statistics."""
    total_keywords: int
    avg_search_volume: Optional[float] = None
    avg_difficulty: Optional[float] = None
    top_sources: dict[str, int]  # source_type -> count
    completion_rate: float  # 0.0 to 1.0