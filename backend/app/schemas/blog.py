from datetime import datetime
from pydantic import BaseModel


class BlogJobCreate(BaseModel):
    keyword: str


class BriefSectionOut(BaseModel):
    heading: str
    type: str
    key_points: list[str]
    estimated_words: int


class AeoOut(BaseModel):
    direct_answer: str
    faqs: list[dict]
    entities: list[str]


class BlogBriefOut(BaseModel):
    id: str
    job_id: str
    selected_title: str
    title_options: list[str]
    meta_description: str
    search_intent: str
    target_word_count: int
    target_audience: str | None
    keyword_variants: list[str]
    outline: list[dict]
    aeo: dict
    tags: list[str]
    approved: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class BlogSectionOut(BaseModel):
    id: str
    section_index: int
    heading: str
    heading_type: str
    content_html: str | None
    word_count: int
    status: str

    model_config = {"from_attributes": True}


class BlogDraftOut(BaseModel):
    id: str
    job_id: str
    title: str
    meta_description: str
    html_content: str
    word_count: int
    seo_score: int
    aeo_score: int
    virality_score: int
    featured_image_url: str | None
    approved: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class BlogJobOut(BaseModel):
    id: str
    brand_id: str
    keyword: str
    status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    brief: BlogBriefOut | None = None
    draft: BlogDraftOut | None = None

    model_config = {"from_attributes": True}


class BlogJobListOut(BaseModel):
    items: list[BlogJobOut]


class ApproveBriefRequest(BaseModel):
    selected_title: str | None = None


class ApproveArticleRequest(BaseModel):
    pass
