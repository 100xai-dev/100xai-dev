from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AuditLog, Brand, BrandKnowledgeSource, BrandProfile, Job
from app.models.base import uuid_str

logger = logging.getLogger(__name__)


class RecoverableError(Exception):
    """Transient errors — retry will likely succeed (network blip, rate limit)."""


class UnrecoverableError(Exception):
    """Permanent errors — retrying won't help (invalid URL, malformed response)."""


# ---------------------------------------------------------------------------
# Top-level pipeline entry (called from RQ worker)
# ---------------------------------------------------------------------------

def run_onboarding_pipeline_job(db: Session, *, job_id: str, brand_id: str) -> None:
    """Sync entry point for RQ. Drives the async pipeline on one event loop."""
    asyncio.run(_run_pipeline_async(db, job_id=job_id, brand_id=brand_id))


async def _run_pipeline_async(db: Session, *, job_id: str, brand_id: str) -> None:
    job = db.query(Job).filter(Job.id == job_id).one_or_none()
    if not job:
        logger.error("Job %s not found", job_id)
        return

    brand = db.query(Brand).filter(Brand.id == brand_id).one_or_none()
    if not brand:
        _mark_failure(db, job_id=job_id, brand_id=brand_id, error_message="Brand not found")
        return

    now = datetime.now(timezone.utc)
    job.status = "RUNNING"
    job.stage = "CRAWLING"
    job.started_at = now
    job.attempt_count = (job.attempt_count or 0) + 1
    db.commit()

    try:
        # ── Stage 1: CRAWL ──────────────────────────────────────────────────
        brand.status = "CRAWLING"
        # Idempotency: wipe any crawled sources from a prior attempt so the
        # rerun does not produce duplicate (brand_id, url) rows. Chunks cascade
        # away with their parent source.
        db.query(BrandKnowledgeSource).filter(
            BrandKnowledgeSource.brand_id == brand.id,
            BrandKnowledgeSource.source_type == "crawled_page",
        ).delete(synchronize_session=False)
        db.commit()

        crawl_result = await _crawl_stage(brand)
        pages = crawl_result.pages

        if not pages:
            raise UnrecoverableError(f"No pages extracted from {brand.website_url}")

        # Persist knowledge sources
        from datetime import timedelta

        source_ids = []
        purge_dt = datetime.now(timezone.utc) + timedelta(days=14)
        for page in pages:
            source = BrandKnowledgeSource(
                id=uuid_str(),
                brand_id=brand.id,
                source_type="crawled_page",
                title=page.metadata.get("title") or page.url,
                url=page.url,
                raw_text=page.raw_text,
                normalized_text=page.normalized_text,
                metadata_json=page.metadata,
                word_count=page.word_count,
                fetched_at=datetime.now(timezone.utc),
                purge_at=purge_dt,
            )
            db.add(source)
            source_ids.append(source)

        job.progress = {
            "pages_crawled": len(pages),
            "failed_urls": crawl_result.failed_urls,
            "partial_crawl": crawl_result.partial_crawl,
        }
        db.commit()

        # ── Stage 2: EXTRACT ─────────────────────────────────────────────────
        job.stage = "EXTRACTING"
        brand.status = "EXTRACTING"
        db.commit()

        manual_hints = job.input_payload.get("manual_hints", {})
        settings = get_settings()

        profile_data = await _extract_stage(
            brand_id=brand.id,
            sources=source_ids,
            manual_hints=manual_hints,
            website_url=brand.website_url,
            extraction_model=settings.extraction_model,
        )

        # Persist profile
        existing_profile = db.query(BrandProfile).filter(BrandProfile.brand_id == brand.id).first()
        if existing_profile:
            for k, v in profile_data.items():
                if hasattr(existing_profile, k):
                    setattr(existing_profile, k, v)
            existing_profile.generation_source = "crawl"
            existing_profile.prompt_version = "v1"
            existing_profile.extraction_model = settings.extraction_model
            existing_profile.raw_extraction = profile_data
        else:
            db.add(BrandProfile(
                id=uuid_str(),
                brand_id=brand.id,
                name=profile_data.get("name", brand.name),
                site_url=profile_data.get("site_url", brand.website_url),
                one_liner=profile_data.get("one_liner", ""),
                industry=profile_data.get("industry"),
                allowed_topics=profile_data.get("allowed_topics", []),
                disallowed_topics=profile_data.get("disallowed_topics", []),
                audience_personas=profile_data.get("audience_personas", []),
                tone_rules=profile_data.get("tone_rules", ""),
                banned_phrases=profile_data.get("banned_phrases", []),
                unique_angle=profile_data.get("unique_angle", ""),
                ctas=profile_data.get("ctas", []),
                proof_points=profile_data.get("proof_points", []),
                messaging_guardrails=profile_data.get("messaging_guardrails", []),
                compliance_keywords=profile_data.get("compliance_keywords", []),
                image_subject_hints=profile_data.get("image_subject_hints"),
                image_palette=profile_data.get("image_palette"),
                visual_direction=profile_data.get("visual_direction"),
                internal_links=[],
                placid_template_id=None,
                image_output_bucket=None,
                default_location="United States",
                default_language="English",
                publish_adapter="none",
                publish_config={},
                generation_source="crawl",
                prompt_version="v1",
                extraction_model=settings.extraction_model,
                raw_extraction=profile_data,
                locked=False,
            ))

        db.commit()

        # ── Stage 3: INGEST ──────────────────────────────────────────────────
        job.stage = "INGESTING"
        brand.status = "INGESTING"
        db.commit()

        sources_for_ingest = (
            db.query(BrandKnowledgeSource)
            .filter(BrandKnowledgeSource.brand_id == brand.id)
            .all()
        )

        vectors_upserted = await _ingest_stage(
            brand_id=brand.id,
            sources=sources_for_ingest,
            db=db,
        )
        job.progress = {**job.progress, "vectors_upserted": vectors_upserted}

        # ── Complete ─────────────────────────────────────────────────────────
        brand.status = "PENDING_REVIEW"
        job.status = "SUCCEEDED"
        job.output_payload = {"brand_id": brand.id, "vectors_upserted": vectors_upserted}
        job.finished_at = datetime.now(timezone.utc)

        db.add(AuditLog(
            org_id=brand.org_id,
            brand_id=brand.id,
            action="brand.onboarding_completed",
            resource_type="brand",
            resource_id=brand.id,
            metadata_json={"job_id": job.id, "pages_crawled": len(pages)},
        ))
        db.commit()
        logger.info("Onboarding pipeline completed for brand %s", brand_id)

    except UnrecoverableError as exc:
        db.rollback()
        _mark_failure(db, job_id=job_id, brand_id=brand_id, error_message=str(exc))
    except RecoverableError as exc:
        db.rollback()
        # If we've burned through max_attempts, give up; otherwise re-raise so
        # the RQ worker retries via the dispatcher's Retry config.
        attempts = (job.attempt_count or 0)
        if attempts >= (job.max_attempts or 3):
            _mark_failure(
                db,
                job_id=job_id,
                brand_id=brand_id,
                error_message=f"max attempts exceeded: {exc}",
            )
            return
        _mark_retry_pending(db, job_id=job_id, error_message=str(exc))
        raise
    except Exception as exc:
        logger.exception("Unexpected error in onboarding pipeline for brand %s", brand_id)
        db.rollback()
        _mark_failure(db, job_id=job_id, brand_id=brand_id, error_message=str(exc))


# ---------------------------------------------------------------------------
# Stage implementations (async, called via asyncio.run())
# ---------------------------------------------------------------------------

async def _crawl_stage(brand: Brand):
    from app.services.crawler import crawl_brand_website, CrawlError
    from app.config import get_settings

    s = get_settings()
    try:
        return await crawl_brand_website(
            seed_url=brand.website_url,
            max_pages=s.crawler_max_pages,
            host_delay=s.crawler_host_delay_sec,
        )
    except CrawlError as exc:
        raise UnrecoverableError(str(exc)) from exc


async def _extract_stage(
    *,
    brand_id: str,
    sources: list,
    manual_hints: dict,
    website_url: str | None,
    extraction_model: str,
):
    from app.services.extractor import extract_brand_profile, ExtractionValidationError

    try:
        return await extract_brand_profile(
            brand_id=brand_id,
            sources=sources,
            manual_hints=manual_hints,
            website_url=website_url,
            extraction_model=extraction_model,
        )
    except ExtractionValidationError as exc:
        raise UnrecoverableError(str(exc)) from exc


async def _ingest_stage(*, brand_id: str, sources: list, db) -> int:
    from app.config import get_settings
    from app.services.ingestion import ingest_brand_knowledge

    s = get_settings()
    if not s.openai_api_key or not s.pinecone_api_key:
        logger.warning("OPENAI_API_KEY or PINECONE_API_KEY not set — skipping Pinecone ingest")
        return 0

    try:
        from pinecone import Pinecone
        pc = Pinecone(api_key=s.pinecone_api_key)
        index = pc.Index(s.pinecone_index_name)
    except Exception as exc:
        logger.warning("Pinecone client init failed — skipping ingest: %s", exc)
        return 0

    try:
        return await ingest_brand_knowledge(
            brand_id=brand_id,
            sources=sources,
            db=db,
            pinecone_index=index,
            openai_api_key=s.openai_api_key,
            embedding_model=s.embedding_model,
        )
    except Exception as exc:
        # Ingest failure is recoverable — brand still gets to PENDING_REVIEW but with 0 vectors
        logger.error("Pinecone ingest failed for brand %s: %s", brand_id, exc)
        return 0


# ---------------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------------

def _mark_failure(db: Session, *, job_id: str, brand_id: str, error_message: str) -> None:
    job = db.query(Job).filter(Job.id == job_id).one_or_none()
    brand = db.query(Brand).filter(Brand.id == brand_id).one_or_none()

    if job:
        job.status = "FAILED"
        job.error_message = error_message
        job.finished_at = datetime.now(timezone.utc)
    if brand:
        brand.status = "FAILED"
        brand.failure_reason = error_message

    # Fall back to job.org_id when the brand is missing (e.g. the job was
    # enqueued against a brand that was deleted before the worker dequeued).
    org_id = (brand.org_id if brand else None) or (job.org_id if job else None)
    if org_id:
        db.add(AuditLog(
            org_id=org_id,
            brand_id=brand_id if brand else None,
            action="job.failed",
            resource_type="job",
            resource_id=job_id,
            metadata_json={"error": error_message},
        ))
    try:
        db.commit()
    except Exception as commit_exc:
        logger.error("Failed to commit failure state: %s", commit_exc)
        db.rollback()


def _mark_retry_pending(db: Session, *, job_id: str, error_message: str) -> None:
    """Annotate a job as 'will be retried by RQ' without marking it failed."""
    job = db.query(Job).filter(Job.id == job_id).one_or_none()
    if job:
        job.status = "QUEUED"
        job.error_message = error_message
    try:
        db.commit()
    except Exception as commit_exc:
        logger.error("Failed to commit retry-pending state: %s", commit_exc)
        db.rollback()
