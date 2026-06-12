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
