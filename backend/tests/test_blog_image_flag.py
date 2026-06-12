"""Tests for the include_image flag flowing through the blog pipeline."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.onboarding import Brand, BrandProfile, Job
from app.services.seo_research import _trigger_content_generation_directly
from tests.conftest import FakeQueue, auth_headers, create_user


def _ready_brand(db: Session, user) -> Brand:
    brand = Brand(
        org_id=user.org_id,
        name="Acme",
        website_url="https://acme.example",
        dna_source="crawl",
        status="READY",
        created_by=user.id,
    )
    db.add(brand)
    db.flush()
    db.add(BrandProfile(
        brand_id=brand.id,
        name="Acme",
        one_liner="We make robots for warehouses.",
        tone_rules="Friendly and concrete.",
        unique_angle="Spatial robotics.",
        generation_source="manual",
    ))
    db.commit()
    return brand


def test_create_blog_job_stores_include_image_false(
    client: TestClient, db_session: Session, fake_queues: dict[str, FakeQueue]
) -> None:
    user = create_user(db_session, "img-flag@example.com")
    brand = _ready_brand(db_session, user)

    resp = client.post(
        f"/v1/brands/{brand.id}/blogs",
        headers=auth_headers(user),
        json={"keyword": "warehouse robots", "include_image": False},
    )
    assert resp.status_code == 201

    job = db_session.query(Job).filter(Job.id == resp.json()["id"]).first()
    assert job.input_payload["include_image"] is False


def test_create_blog_job_defaults_include_image_true(
    client: TestClient, db_session: Session, fake_queues: dict[str, FakeQueue]
) -> None:
    user = create_user(db_session, "img-default@example.com")
    brand = _ready_brand(db_session, user)

    resp = client.post(
        f"/v1/brands/{brand.id}/blogs",
        headers=auth_headers(user),
        json={"keyword": "warehouse robots"},
    )
    assert resp.status_code == 201

    job = db_session.query(Job).filter(Job.id == resp.json()["id"]).first()
    assert job.input_payload["include_image"] is True


def test_direct_content_trigger_propagates_include_image(
    db_session: Session, fake_queues: dict[str, FakeQueue]
) -> None:
    user = create_user(db_session, "img-prop@example.com")
    brand = _ready_brand(db_session, user)

    parent = Job(
        org_id=user.org_id,
        brand_id=brand.id,
        job_type="keyword_research",
        status="RUNNING",
        stage="KEYWORD",
        input_payload={
            "keyword": "warehouse robots",
            "blog_job_id": "blog-1",
            "include_image": False,
        },
    )
    db_session.add(parent)
    db_session.commit()

    _trigger_content_generation_directly(
        db_session, parent, "warehouse robots", parent.input_payload
    )

    content_job = db_session.query(Job).filter(
        Job.job_type == "content_generation"
    ).first()
    assert content_job is not None
    assert content_job.input_payload["include_image"] is False


def test_generate_featured_image_brands_when_logo_set(
    db_session: Session, monkeypatch
) -> None:
    import asyncio

    from app.services import content_generation

    user = create_user(db_session, "img-brand@example.com")
    brand = _ready_brand(db_session, user)
    profile = db_session.query(BrandProfile).filter(
        BrandProfile.brand_id == brand.id
    ).first()
    profile.logo_url = "https://acme.example/logo.png"
    db_session.commit()

    job = Job(
        org_id=user.org_id,
        brand_id=brand.id,
        job_type="content_generation",
        status="RUNNING",
        stage="CONTENT",
        input_payload={"keyword": "warehouse robots"},
    )
    db_session.add(job)
    db_session.commit()

    class FakeArticle:
        meta_title = "Warehouse Robots Guide"

    async def fake_prompt(article, brand_profile):
        return {"Complete_Prompt": "robots in a warehouse"}

    class FakeLeonardo:
        async def generate_image(self, prompt):
            return "https://cdn.leonardo.example/raw.jpg"

    async def fake_brand(image_url, logo_url, key):
        assert image_url == "https://cdn.leonardo.example/raw.jpg"
        assert logo_url == "https://acme.example/logo.png"
        return "http://localhost:9000/bucket/branded.jpg"

    monkeypatch.setattr(content_generation, "generate_image_prompt", fake_prompt)
    monkeypatch.setattr(content_generation, "LeonardoService", FakeLeonardo)
    monkeypatch.setattr(content_generation, "brand_featured_image", fake_brand)

    url = asyncio.run(content_generation.generate_featured_image(
        FakeArticle(), profile, job, db_session
    ))
    assert url == "http://localhost:9000/bucket/branded.jpg"


def test_generate_featured_image_falls_back_when_branding_fails(
    db_session: Session, monkeypatch
) -> None:
    import asyncio

    from app.services import content_generation

    user = create_user(db_session, "img-fallback@example.com")
    brand = _ready_brand(db_session, user)
    profile = db_session.query(BrandProfile).filter(
        BrandProfile.brand_id == brand.id
    ).first()
    profile.logo_url = "https://acme.example/logo.png"
    db_session.commit()

    job = Job(
        org_id=user.org_id,
        brand_id=brand.id,
        job_type="content_generation",
        status="RUNNING",
        stage="CONTENT",
        input_payload={"keyword": "warehouse robots"},
    )
    db_session.add(job)
    db_session.commit()

    class FakeArticle:
        meta_title = "Warehouse Robots Guide"

    async def fake_prompt(article, brand_profile):
        return {"Complete_Prompt": "robots in a warehouse"}

    class FakeLeonardo:
        async def generate_image(self, prompt):
            return "https://cdn.leonardo.example/raw.jpg"

    async def fake_brand(image_url, logo_url, key):
        return None  # branding failed (e.g. S3 not configured)

    monkeypatch.setattr(content_generation, "generate_image_prompt", fake_prompt)
    monkeypatch.setattr(content_generation, "LeonardoService", FakeLeonardo)
    monkeypatch.setattr(content_generation, "brand_featured_image", fake_brand)

    url = asyncio.run(content_generation.generate_featured_image(
        FakeArticle(), profile, job, db_session
    ))
    assert url == "https://cdn.leonardo.example/raw.jpg"
