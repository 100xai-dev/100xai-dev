"""Tests for the onboarding wizard status aggregation endpoint (W4)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import IntegrationAccount
from app.models.base import uuid_str
from app.models.onboarding import Brand
from tests.conftest import auth_headers, create_user


def _brand(db: Session, user, status: str = "DRAFT") -> Brand:
    brand = Brand(org_id=user.org_id, name="Acme", website_url="https://acme.example",
                  dna_source="crawl", status=status, created_by=user.id)
    db.add(brand)
    db.commit()
    return brand


def test_onboarding_status_empty_brand(client: TestClient, db_session: Session) -> None:
    user = create_user(db_session, "onb-status@example.com")
    brand = _brand(db_session, user)

    resp = client.get(f"/v1/brands/{brand.id}/onboarding-status", headers=auth_headers(user))
    assert resp.status_code == 200
    body = resp.json()
    assert body["steps"]["profile_ready"] is False
    assert body["steps"]["has_active_integration"] is False
    assert body["is_complete"] is False
    assert body["completion"] == 0


def test_onboarding_status_counts_integration(client: TestClient, db_session: Session) -> None:
    user = create_user(db_session, "onb-status2@example.com")
    brand = _brand(db_session, user, status="READY")
    db_session.add(IntegrationAccount(
        id=uuid_str(), brand_id=brand.id, provider="wordpress", status="active",
        config={}, created_by=user.id,
    ))
    db_session.commit()

    resp = client.get(f"/v1/brands/{brand.id}/onboarding-status", headers=auth_headers(user))
    assert resp.status_code == 200
    body = resp.json()
    assert body["steps"]["has_active_integration"] is True
    assert body["steps"]["integration_provider"] == "wordpress"
    assert body["is_complete"] is True


def test_onboarding_status_404_for_other_org(client: TestClient, db_session: Session) -> None:
    owner = create_user(db_session, "onb-owner@example.com")
    brand = _brand(db_session, owner)
    other = create_user(db_session, "onb-other@example.com")

    resp = client.get(f"/v1/brands/{brand.id}/onboarding-status", headers=auth_headers(other))
    assert resp.status_code == 404
