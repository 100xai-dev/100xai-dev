from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Brand, Job
from app.repositories.jobs import JobsRepository
from tests.conftest import FakeQueue, auth_headers, create_user


def test_crawl_path_enqueues_onboarding_job(
    client: TestClient,
    db_session: Session,
    fake_queues: dict[str, FakeQueue],
) -> None:
    user = create_user(db_session, "queue-crawl@example.com", plan_code="pro")

    response = client.post(
        "/v1/brands",
        headers=auth_headers(user),
        json={"name": "Acme", "website_url": "https://acme.test", "dna_source": "crawl"},
    )

    assert response.status_code == 201
    brand_id = response.json()["brand_id"]
    jobs = db_session.query(Job).filter(Job.brand_id == brand_id).all()
    assert len(jobs) == 1
    assert jobs[0].job_type == "brand.onboard"
    assert jobs[0].status == "QUEUED"

    onboarding = fake_queues["onboarding"]
    assert len(onboarding.calls) == 1
    call = onboarding.calls[0]
    assert call.func == "worker.tasks.onboarding.run_onboarding_pipeline"
    assert call.kwargs == {"job_id": jobs[0].id, "brand_id": brand_id}
    assert call.job_id == jobs[0].id


def test_manual_path_does_not_enqueue(
    client: TestClient,
    db_session: Session,
    fake_queues: dict[str, FakeQueue],
) -> None:
    user = create_user(db_session, "queue-manual@example.com", plan_code="pro")

    response = client.post(
        "/v1/brands",
        headers=auth_headers(user),
        json={"name": "Manual Brand", "dna_source": "manual"},
    )

    assert response.status_code == 201
    assert db_session.query(Job).count() == 0
    assert fake_queues.get("onboarding", FakeQueue("onboarding")).calls == []


def test_jobs_repository_create_writes_row_with_org_scope(db_session: Session) -> None:
    user = create_user(db_session, "jobs-repo@example.com")
    brand = Brand(
        org_id=user.org_id,
        name="Acme",
        website_url="https://acme.test",
        dna_source="crawl",
        status="CRAWLING",
        created_by=user.id,
    )
    db_session.add(brand)
    db_session.flush()

    job = JobsRepository(db_session).create(
        org_id=user.org_id,
        brand_id=brand.id,
        job_type="brand.onboard",
        input_payload={"brand_id": brand.id},
    )

    assert job.id is not None
    assert job.org_id == user.org_id
    assert job.brand_id == brand.id
    assert job.job_type == "brand.onboard"
    assert job.status == "QUEUED"


def test_enqueue_failure_does_not_lose_job_row(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    user = create_user(db_session, "queue-failure@example.com", plan_code="pro")

    def boom(self, *, job_id: str, brand_id: str) -> None:
        raise RuntimeError("redis down")

    monkeypatch.setattr(
        "app.services.job_dispatcher.JobDispatcher.enqueue_onboarding",
        boom,
    )
    response = client.post(
        "/v1/brands",
        headers=auth_headers(user),
        json={"name": "Acme", "website_url": "https://acme.test", "dna_source": "crawl"},
    )

    assert response.status_code == 201
    assert (
        db_session.query(Job)
        .filter(Job.job_type == "brand.onboard", Job.status == "QUEUED")
        .count()
        == 1
    )

