"""Tests for the always-require-review publishing gate (W2)."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.base import uuid_str
from app.models.blog import BlogDraft, BlogJob
from app.models.onboarding import Brand
from app.models.schedule import BlogSchedule, ScheduleStatus
from tests.conftest import FakeQueue, auth_headers, create_user


def _brand(db: Session, user) -> Brand:
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
    return brand


def _schedule_with_draft(db: Session, user, brand, *, with_draft: bool = True) -> BlogSchedule:
    job_id = uuid_str()
    db.add(BlogJob(id=job_id, org_id=user.org_id, brand_id=brand.id, created_by=user.id,
                   keyword="spatial robotics", status="GENERATING"))
    if with_draft:
        db.add(BlogDraft(id=uuid_str(), job_id=job_id, title="Spatial Robotics 101",
                         meta_description="A primer.", html_content="<h1>Hi</h1>"))
    schedule = BlogSchedule(
        id=uuid_str(),
        org_id=user.org_id,
        brand_id=brand.id,
        title="spatial robotics",
        scheduled_at=datetime.now(timezone.utc) + timedelta(days=1),
        blog_job_id=job_id,
        target_keyword="spatial robotics",
        target_channels=["wordpress"],
        status=ScheduleStatus.SCHEDULED,
        created_by=user.id,
    )
    db.add(schedule)
    db.commit()
    return schedule


def test_review_queue_promotes_ready_draft(client: TestClient, db_session: Session) -> None:
    user = create_user(db_session, "review-admin@example.com")
    brand = _brand(db_session, user)
    schedule = _schedule_with_draft(db_session, user, brand)

    resp = client.get(f"/v1/schedules/brands/{brand.id}/review-queue", headers=auth_headers(user))
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["id"] == schedule.id
    assert items[0]["status"] == "PENDING_APPROVAL"
    assert items[0]["draft"]["title"] == "Spatial Robotics 101"

    db_session.refresh(schedule)
    assert schedule.status == ScheduleStatus.PENDING_APPROVAL


def test_review_queue_excludes_unready_schedules(client: TestClient, db_session: Session) -> None:
    user = create_user(db_session, "review-admin2@example.com")
    brand = _brand(db_session, user)
    _schedule_with_draft(db_session, user, brand, with_draft=False)

    resp = client.get(f"/v1/schedules/brands/{brand.id}/review-queue", headers=auth_headers(user))
    assert resp.status_code == 200
    assert resp.json() == []


def test_approve_enqueues_publish_and_sets_publishing(
    client: TestClient, db_session: Session, fake_queues: dict[str, FakeQueue]
) -> None:
    user = create_user(db_session, "approver@example.com")
    brand = _brand(db_session, user)
    schedule = _schedule_with_draft(db_session, user, brand)

    resp = client.post(f"/v1/schedules/{schedule.id}/approve", headers=auth_headers(user))
    assert resp.status_code == 200
    assert resp.json()["status"] == "publishing"

    db_session.refresh(schedule)
    assert schedule.status == ScheduleStatus.PUBLISHING
    assert schedule.approved_by == user.id
    assert schedule.approved_at is not None

    enqueued = [c for q in fake_queues.values() for c in q.calls]
    assert any("publish_approved_schedule" in c.func for c in enqueued)


def test_reject_cancels_without_publishing(
    client: TestClient, db_session: Session, fake_queues: dict[str, FakeQueue]
) -> None:
    user = create_user(db_session, "rejecter@example.com")
    brand = _brand(db_session, user)
    schedule = _schedule_with_draft(db_session, user, brand)

    resp = client.post(f"/v1/schedules/{schedule.id}/reject",
                       headers=auth_headers(user), json={"reason": "off-brand"})
    assert resp.status_code == 200
    db_session.refresh(schedule)
    assert schedule.status == ScheduleStatus.CANCELLED
    assert schedule.last_error == "off-brand"

    enqueued = [c for q in fake_queues.values() for c in q.calls]
    assert not any("publish" in c.func for c in enqueued)


def test_viewer_cannot_approve(client: TestClient, db_session: Session) -> None:
    admin = create_user(db_session, "owner@example.com")
    viewer = create_user(db_session, "viewer@example.com", role="viewer")
    # viewer must be in the same org to reach the row
    viewer.org_id = admin.org_id
    db_session.commit()
    brand = _brand(db_session, admin)
    schedule = _schedule_with_draft(db_session, admin, brand)

    resp = client.post(f"/v1/schedules/{schedule.id}/approve", headers=auth_headers(viewer))
    assert resp.status_code == 403
    db_session.refresh(schedule)
    assert schedule.status == ScheduleStatus.SCHEDULED
