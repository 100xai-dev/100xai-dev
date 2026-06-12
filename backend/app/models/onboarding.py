from sqlalchemy import Uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, utcnow, uuid_str


class Brand(Base, TimestampMixin):
    __tablename__ = "brands"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_str)
    org_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    website_url: Mapped[str | None] = mapped_column(String)
    dna_source: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="DRAFT")
    failure_reason: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("users.id"), nullable=False)

    jobs: Mapped[list["Job"]] = relationship(
        back_populates="brand", cascade="all, delete-orphan"
    )
    integration_accounts: Mapped[list["IntegrationAccount"]] = relationship(
        back_populates="brand", cascade="all, delete-orphan"
    )
    schedules: Mapped[list["BlogSchedule"]] = relationship(
        "BlogSchedule", back_populates="brand", cascade="all, delete-orphan"
    )


class BrandProfile(Base, TimestampMixin):
    __tablename__ = "brand_profiles"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_str)
    brand_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("brands.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    site_url: Mapped[str | None] = mapped_column(String)
    one_liner: Mapped[str] = mapped_column(Text, nullable=False)
    industry: Mapped[str | None] = mapped_column(String)
    allowed_topics: Mapped[list[str]] = mapped_column(JSON, default=list)
    disallowed_topics: Mapped[list[str]] = mapped_column(JSON, default=list)
    audience_personas: Mapped[list[str]] = mapped_column(JSON, default=list)
    tone_rules: Mapped[str] = mapped_column(Text, nullable=False)
    banned_phrases: Mapped[list[str]] = mapped_column(JSON, default=list)
    unique_angle: Mapped[str] = mapped_column(Text, nullable=False)
    ctas: Mapped[list[str]] = mapped_column(JSON, default=list)
    proof_points: Mapped[list[str]] = mapped_column(JSON, default=list)
    messaging_guardrails: Mapped[list[str]] = mapped_column(JSON, default=list)
    compliance_keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    image_subject_hints: Mapped[str | None] = mapped_column(Text)
    image_palette: Mapped[str | None] = mapped_column(Text)
    visual_direction: Mapped[str | None] = mapped_column(Text)
    logo_url: Mapped[str | None] = mapped_column(String)
    internal_links: Mapped[list[dict]] = mapped_column(JSON, default=list)
    placid_template_id: Mapped[str | None] = mapped_column(String)
    image_output_bucket: Mapped[str | None] = mapped_column(String)
    default_location: Mapped[str] = mapped_column(String, nullable=False, default="United States")
    default_language: Mapped[str] = mapped_column(String, nullable=False, default="English")
    publish_adapter: Mapped[str] = mapped_column(String, nullable=False, default="none")
    publish_config: Mapped[dict] = mapped_column(JSON, default=dict)
    generation_source: Mapped[str] = mapped_column(String, nullable=False)
    prompt_version: Mapped[str | None] = mapped_column(String)
    extraction_model: Mapped[str | None] = mapped_column(String)
    raw_extraction: Mapped[dict | None] = mapped_column(JSON)
    locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("users.id"))


class BrandKnowledgeSource(Base):
    __tablename__ = "brand_knowledge_sources"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_str)
    brand_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("brands.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str | None] = mapped_column(String)
    url: Mapped[str | None] = mapped_column(String)
    storage_key: Mapped[str | None] = mapped_column(String)
    raw_text: Mapped[str | None] = mapped_column(Text)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    word_count: Mapped[int | None] = mapped_column(Integer)
    screenshot_url: Mapped[str | None] = mapped_column(String)
    html_content: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    purge_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BrandKnowledgeChunk(Base):
    __tablename__ = "brand_knowledge_chunks"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_str)
    brand_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("brands.id", ondelete="CASCADE"))
    source_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("brand_knowledge_sources.id", ondelete="CASCADE"),
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    vector_id: Mapped[str] = mapped_column(String, nullable=False)
    embedding_model: Mapped[str] = mapped_column(String, nullable=False)
    namespace: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class IntegrationAccount(Base, TimestampMixin):
    __tablename__ = "integration_accounts"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_str)
    brand_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("brands.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    display_label: Mapped[str | None] = mapped_column(String)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("users.id"), nullable=False)

    brand: Mapped[Brand] = relationship(back_populates="integration_accounts")


class IntegrationToken(Base, TimestampMixin):
    __tablename__ = "integration_tokens"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_str)
    integration_account_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("integration_accounts.id", ondelete="CASCADE"),
        unique=True,
    )
    encrypted_payload: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    encryption_key_id: Mapped[str] = mapped_column(String, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_str)
    org_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("organizations.id"), nullable=False)
    brand_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("brands.id", ondelete="CASCADE"))
    job_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="NEW")
    stage: Mapped[str | None] = mapped_column(String)
    progress: Mapped[dict] = mapped_column(JSON, default=dict)
    input_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    output_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)
    error_details: Mapped[dict | None] = mapped_column(JSON)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    brand: Mapped[Brand | None] = relationship(back_populates="jobs")
