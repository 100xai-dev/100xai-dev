"""onboarding subsystem

Revision ID: 20260527_0001
Revises:
Create Date: 2026-05-27
"""

from alembic import op
import sqlalchemy as sa

revision = "20260527_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("name", sa.Text()),
        sa.Column("role", sa.Text(), nullable=False, server_default="admin"),
        sa.Column("org_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("role IN ('admin', 'team_member', 'viewer')", name="ck_users_role"),
    )
    op.create_table(
        "brands",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("website_url", sa.Text()),
        sa.Column("dna_source", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="DRAFT"),
        sa.Column("failure_reason", sa.Text()),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("dna_source IN ('crawl', 'manual')", name="ck_brands_dna_source"),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'CRAWLING', 'EXTRACTING', 'INGESTING', 'PENDING_REVIEW', 'READY', 'FAILED')",
            name="ck_brands_status",
        ),
    )
    op.create_index("idx_brands_org_status", "brands", ["org_id", "status"])
    op.create_index("idx_brands_created_at", "brands", ["created_at"])
    op.create_table(
        "brand_profiles",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("brand_id", sa.Uuid(), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("site_url", sa.Text()),
        sa.Column("one_liner", sa.Text(), nullable=False),
        sa.Column("industry", sa.Text()),
        sa.Column("allowed_topics", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("disallowed_topics", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("audience_personas", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("tone_rules", sa.Text(), nullable=False),
        sa.Column("banned_phrases", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("unique_angle", sa.Text(), nullable=False),
        sa.Column("ctas", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("proof_points", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("messaging_guardrails", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("compliance_keywords", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("image_subject_hints", sa.Text()),
        sa.Column("image_palette", sa.Text()),
        sa.Column("visual_direction", sa.Text()),
        sa.Column("internal_links", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("placid_template_id", sa.Text()),
        sa.Column("image_output_bucket", sa.Text()),
        sa.Column("default_location", sa.Text(), nullable=False, server_default="United States"),
        sa.Column("default_language", sa.Text(), nullable=False, server_default="English"),
        sa.Column("publish_adapter", sa.Text(), nullable=False, server_default="none"),
        sa.Column("publish_config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("generation_source", sa.Text(), nullable=False),
        sa.Column("prompt_version", sa.Text()),
        sa.Column("extraction_model", sa.Text()),
        sa.Column("raw_extraction", sa.JSON()),
        sa.Column("locked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("locked_at", sa.DateTime(timezone=True)),
        sa.Column("locked_by", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("generation_source IN ('crawl', 'manual', 'hybrid')", name="ck_profiles_generation_source"),
        sa.CheckConstraint("publish_adapter IN ('none', 'wordpress', 'shopify', 'webflow', 'custom_api')", name="ck_profiles_publish_adapter"),
    )
    op.create_table(
        "brand_knowledge_sources",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("brand_id", sa.Uuid(), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text()),
        sa.Column("url", sa.Text()),
        sa.Column("storage_key", sa.Text()),
        sa.Column("raw_text", sa.Text()),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("word_count", sa.Integer()),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("purge_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "source_type IN ('crawled_page', 'uploaded_doc', 'manual_text', 'manual_form_field')",
            name="ck_sources_type",
        ),
    )
    op.create_table(
        "brand_knowledge_chunks",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("brand_id", sa.Uuid(), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", sa.Uuid(), sa.ForeignKey("brand_knowledge_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("vector_id", sa.Text(), nullable=False),
        sa.Column("embedding_model", sa.Text(), nullable=False),
        sa.Column("namespace", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("source_id", "chunk_index", name="uq_chunks_source_index"),
    )
    op.create_table(
        "integration_accounts",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("brand_id", sa.Uuid(), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("display_label", sa.Text()),
        sa.Column("config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("last_tested_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("brand_id", "provider", name="uq_integrations_brand_provider"),
    )
    op.create_table(
        "integration_tokens",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("integration_account_id", sa.Uuid(), sa.ForeignKey("integration_accounts.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("encrypted_payload", sa.LargeBinary(), nullable=False),
        sa.Column("encryption_key_id", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("brand_id", sa.Uuid(), sa.ForeignKey("brands.id", ondelete="CASCADE")),
        sa.Column("job_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="NEW"),
        sa.Column("stage", sa.Text()),
        sa.Column("progress", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("input_payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("output_payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text()),
        sa.Column("error_details", sa.JSON()),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("brand_id", sa.Uuid(), sa.ForeignKey("brands.id", ondelete="SET NULL")),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("resource_type", sa.Text()),
        sa.Column("resource_id", sa.Uuid()),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    for table in [
        "audit_logs",
        "jobs",
        "integration_tokens",
        "integration_accounts",
        "brand_knowledge_chunks",
        "brand_knowledge_sources",
        "brand_profiles",
        "brands",
        "users",
        "organizations",
    ]:
        op.drop_table(table)

