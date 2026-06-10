import pytest
from sqlalchemy.orm import Session

from app.models import AuditLog, Brand, BrandKnowledgeSource, BrandProfile, Job
from app.services.onboarding_pipeline import run_onboarding_pipeline_job
from tests.conftest import create_user


def _create_crawl_brand_with_job(db_session: Session) -> tuple[Brand, Job]:
    user = create_user(db_session, "worker-onboarding@example.com")
    brand = Brand(
        org_id=user.org_id,
        name="Acme Robotics",
        website_url="https://acme.example",
        dna_source="crawl",
        status="CRAWLING",
        created_by=user.id,
    )
    db_session.add(brand)
    db_session.flush()
    job = Job(
        org_id=user.org_id,
        brand_id=brand.id,
        job_type="brand.onboard",
        status="QUEUED",
        stage="CRAWLING",
        input_payload={"brand_id": brand.id, "seed_url": brand.website_url},
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(brand)
    db_session.refresh(job)
    return brand, job


@pytest.fixture
def stub_pipeline_externals(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace network-bound stages with deterministic fakes so the pipeline
    can be exercised end-to-end without OpenRouter, Pinecone, or live HTTP."""
    from dataclasses import dataclass

    @dataclass
    class _FakePage:
        url: str
        raw_text: str
        normalized_text: str
        word_count: int
        metadata: dict
        screenshot_url: str | None = None
        html_content: str | None = None

    @dataclass
    class _FakeResult:
        pages: list
        failed_urls: list
        partial_crawl: bool

    async def fake_crawl_stage(brand):
        page = _FakePage(
            url=brand.website_url,
            raw_text="Acme Robotics builds spatial automation systems.",
            normalized_text="Acme Robotics builds spatial automation systems.",
            word_count=7,
            metadata={"title": "Acme Robotics"},
        )
        return _FakeResult(pages=[page], failed_urls=[], partial_crawl=False)

    async def fake_extract_stage(*, brand_id, sources, manual_hints, website_url, extraction_model):
        return {
            "name": "Acme Robotics",
            "site_url": website_url or "https://acme.example",
            "one_liner": "Acme Robotics builds spatial automation systems.",
            "industry": "industrial robotics",
            "allowed_topics": ["spatial robotics", "kinetic manufacturing"],
            "disallowed_topics": [],
            "audience_personas": ["aerospace engineers building automation pipelines"],
            "tone_rules": "Direct, technically rigorous, optimistic about engineering.",
            "banned_phrases": ["disruptive", "synergy"],
            "unique_angle": "Self-sustaining spatial infrastructure.",
            "ctas": ["Schedule a demo"],
            "proof_points": [],
            "messaging_guardrails": [],
            "compliance_keywords": [],
            "image_subject_hints": None,
            "image_palette": None,
            "visual_direction": None,
        }

    monkeypatch.setattr(
        "app.services.onboarding_pipeline._crawl_stage", fake_crawl_stage
    )
    monkeypatch.setattr(
        "app.services.onboarding_pipeline._extract_stage", fake_extract_stage
    )


def test_run_onboarding_pipeline_transitions_and_persists_source(
    db_session: Session, stub_pipeline_externals: None
) -> None:
    brand, job = _create_crawl_brand_with_job(db_session)

    run_onboarding_pipeline_job(db_session, job_id=job.id, brand_id=brand.id)

    db_session.refresh(job)
    db_session.refresh(brand)
    assert job.status == "SUCCEEDED"
    assert job.stage == "INGESTING"
    assert brand.status == "PENDING_REVIEW"

    source = (
        db_session.query(BrandKnowledgeSource)
        .filter(BrandKnowledgeSource.brand_id == brand.id, BrandKnowledgeSource.source_type == "crawled_page")
        .one()
    )
    assert source.url == brand.website_url
    assert source.normalized_text != ""

    profile = db_session.query(BrandProfile).filter(BrandProfile.brand_id == brand.id).one()
    assert profile.generation_source == "crawl"
    assert profile.locked is False


def test_run_onboarding_pipeline_marks_failure_for_missing_brand(db_session: Session) -> None:
    user = create_user(db_session, "worker-onboarding-fail@example.com")
    job = Job(
        org_id=user.org_id,
        brand_id="00000000-0000-0000-0000-0000000000ff",
        job_type="brand.onboard",
        status="QUEUED",
        stage="CRAWLING",
        input_payload={"brand_id": "00000000-0000-0000-0000-0000000000ff"},
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    run_onboarding_pipeline_job(db_session, job_id=job.id, brand_id="00000000-0000-0000-0000-0000000000ff")

    db_session.refresh(job)
    assert job.status == "FAILED"
    assert job.error_message

    audit = db_session.query(AuditLog).filter(AuditLog.org_id == user.org_id, AuditLog.action == "job.failed").one()
    assert audit.resource_type == "job"
    assert audit.resource_id == job.id
