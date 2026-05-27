from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class PublishAdapter(StrEnum):
    NONE = "none"
    WORDPRESS = "wordpress"
    SHOPIFY = "shopify"
    WEBFLOW = "webflow"
    CUSTOM_API = "custom_api"


class InternalLink(BaseModel):
    label: str
    url: HttpUrl


class BrandProfileContent(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    site_url: HttpUrl | None = None
    one_liner: str = Field(..., min_length=10, max_length=500)
    industry: str | None = None
    allowed_topics: list[str] = Field(..., min_length=1)
    disallowed_topics: list[str] = Field(default_factory=list)
    audience_personas: list[str] = Field(..., min_length=1)
    tone_rules: str = Field(..., min_length=10)
    banned_phrases: list[str] = Field(default_factory=list)
    unique_angle: str = Field(..., min_length=5)
    ctas: list[str] = Field(..., min_length=1)
    proof_points: list[str] = Field(default_factory=list)
    messaging_guardrails: list[str] = Field(default_factory=list)
    compliance_keywords: list[str] = Field(default_factory=list)
    image_subject_hints: str | None = None
    image_palette: str | None = None
    visual_direction: str | None = None


class OperationalConfig(BaseModel):
    internal_links: list[InternalLink] = Field(default_factory=list)
    placid_template_id: str | None = None
    image_output_bucket: str | None = None
    default_location: str = "United States"
    default_language: str = "English"
    publish_adapter: PublishAdapter = PublishAdapter.NONE
    publish_config: dict[str, Any] = Field(default_factory=dict)


class BrandProfilePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    site_url: HttpUrl | None = None
    one_liner: str | None = Field(default=None, min_length=10, max_length=500)
    industry: str | None = None
    allowed_topics: list[str] | None = None
    disallowed_topics: list[str] | None = None
    audience_personas: list[str] | None = None
    tone_rules: str | None = Field(default=None, min_length=10)
    banned_phrases: list[str] | None = None
    unique_angle: str | None = Field(default=None, min_length=5)
    ctas: list[str] | None = None
    proof_points: list[str] | None = None
    messaging_guardrails: list[str] | None = None
    compliance_keywords: list[str] | None = None
    image_subject_hints: str | None = None
    image_palette: str | None = None
    visual_direction: str | None = None
    internal_links: list[InternalLink] | None = None
    placid_template_id: str | None = None
    image_output_bucket: str | None = None
    default_location: str | None = None
    default_language: str | None = None
    publish_adapter: PublishAdapter | None = None
    publish_config: dict[str, Any] | None = None


class BrandProfileFull(BrandProfileContent, OperationalConfig):
    id: str
    brand_id: str
    generation_source: str
    prompt_version: str | None
    extraction_model: str | None
    locked: bool
    locked_at: datetime | None
    locked_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

