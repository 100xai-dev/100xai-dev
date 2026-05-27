from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Brand, Job


def test_create_crawl_brand_persists_brand_and_onboard_job(
    client: TestClient,
    db_session: Session,
) -> None:
    from tests.conftest import auth_headers, create_user

    user = create_user(db_session, "admin@example.com")

    response = client.post(
        "/v1/brands",
        headers=auth_headers(user),
        json={
            "name": "Acme",
            "website_url": "https://acme.com",
            "dna_source": "crawl",
            "manual_hints": {"target_audience_notes": "B2B founders"},
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "CRAWLING"
    assert body["dna_source"] == "crawl"
    assert body["job_id"] is not None

    brand = db_session.query(Brand).filter_by(id=body["brand_id"]).one()
    assert brand.org_id == user.org_id
    assert brand.status == "CRAWLING"

    job = db_session.query(Job).filter_by(id=body["job_id"]).one()
    assert job.job_type == "brand.onboard"
    assert job.status == "NEW"


def test_create_manual_brand_does_not_create_onboard_job(
    client: TestClient,
    db_session: Session,
) -> None:
    from tests.conftest import auth_headers, create_user

    user = create_user(db_session, "team@example.com", role="team_member")

    response = client.post(
        "/v1/brands",
        headers=auth_headers(user),
        json={"name": "Manual Brand", "dna_source": "manual"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "DRAFT"
    assert body["job_id"] is None
    assert db_session.query(Job).count() == 0


def test_list_brands_is_tenant_scoped(client: TestClient, db_session: Session) -> None:
    from tests.conftest import auth_headers, create_user

    first = create_user(db_session, "first@example.com")
    second = create_user(db_session, "second@example.com")

    client.post(
        "/v1/brands",
        headers=auth_headers(first),
        json={"name": "Visible", "dna_source": "manual"},
    )
    client.post(
        "/v1/brands",
        headers=auth_headers(second),
        json={"name": "Hidden", "dna_source": "manual"},
    )

    response = client.get("/v1/brands", headers=auth_headers(first))

    assert response.status_code == 200
    assert [item["name"] for item in response.json()["items"]] == ["Visible"]


def test_approve_locks_pending_review_profile(client: TestClient, db_session: Session) -> None:
    from tests.conftest import auth_headers, create_user

    user = create_user(db_session, "approver@example.com")
    create_response = client.post(
        "/v1/brands",
        headers=auth_headers(user),
        json={"name": "Manual Brand", "dna_source": "manual"},
    )
    brand_id = create_response.json()["brand_id"]

    profile_response = client.post(
        f"/v1/brands/{brand_id}/profile",
        headers=auth_headers(user),
        json={
            "name": "Manual Brand",
            "one_liner": "Manual Brand helps teams ship better marketing.",
            "allowed_topics": ["brand strategy"],
            "audience_personas": ["internal marketing teams building repeatable workflows"],
            "tone_rules": "Clear, practical, and specific. Avoid exaggerated claims.",
            "banned_phrases": ["delve"],
            "unique_angle": "Persistent brand memory",
            "ctas": ["Book a call"],
        },
    )
    assert profile_response.status_code == 201

    approve_response = client.post(f"/v1/brands/{brand_id}/approve", headers=auth_headers(user))

    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "READY"

    patch_response = client.patch(
        f"/v1/brands/{brand_id}/profile",
        headers=auth_headers(user),
        json={"one_liner": "This should not apply after lock."},
    )
    assert patch_response.status_code == 409

