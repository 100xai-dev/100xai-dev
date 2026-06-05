# app/schemas/content_generation.py
from pydantic import BaseModel, Field


class ContentGenerationRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=200)
    serp_analysis_job_id: str | None = None


class ContentGenerationResponse(BaseModel):
    job_id: str
    status: str
    message: str = "Content generation started"