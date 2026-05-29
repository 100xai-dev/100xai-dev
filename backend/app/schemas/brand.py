from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, model_validator


class DNASource(StrEnum):
    CRAWL = "crawl"
    MANUAL = "manual"


class BrandStatus(StrEnum):
    DRAFT = "DRAFT"
    CRAWLING = "CRAWLING"
    EXTRACTING = "EXTRACTING"
    INGESTING = "INGESTING"
    PENDING_REVIEW = "PENDING_REVIEW"
    READY = "READY"
    FAILED = "FAILED"
    PENDING_DELETE = "PENDING_DELETE"


class BrandCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    website_url: HttpUrl | None = None
    dna_source: DNASource
    manual_hints: dict[str, Any] = Field(default_factory=dict)
    uploaded_source_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def crawl_requires_website(self) -> "BrandCreate":
        if self.dna_source == DNASource.CRAWL and self.website_url is None:
            raise ValueError("website_url is required when dna_source is crawl")
        return self


class BrandCreateResponse(BaseModel):
    brand_id: str
    status: BrandStatus
    dna_source: DNASource
    job_id: str | None


class ActiveJobSummary(BaseModel):
    id: str
    status: str
    stage: str | None
    progress: dict[str, Any]


class BrandSummary(BaseModel):
    id: str
    name: str
    website_url: str | None
    dna_source: DNASource
    status: BrandStatus
    failure_reason: str | None
    created_by: str
    created_at: datetime
    updated_at: datetime
    channel_readiness: dict[str, str | None] = Field(default_factory=dict)
    active_job: ActiveJobSummary | None = None


class BrandListResponse(BaseModel):
    items: list[BrandSummary]


class ApproveBrandResponse(BaseModel):
    brand_id: str
    status: BrandStatus
    locked_at: datetime
    locked_by: str


class DeleteBrandResponse(BaseModel):
    job_id: str
