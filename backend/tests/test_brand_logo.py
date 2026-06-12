"""Tests for the brand logo_url profile field."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.onboarding import Brand, BrandProfile
from tests.conftest import auth_headers, create_user


def _reviewable_brand(db: Session, user) -> Brand:
    """Brand in PENDING_REVIEW with an unlocked profile (patchable state)."""
    brand = Brand(
        org_id=user.org_id,
        name="Acme",
        website_url="https://acme.example",
        dna_source="crawl",
        status="PENDING_REVIEW",
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


def test_patch_profile_sets_logo_url(
    client: TestClient, db_session: Session
) -> None:
    user = create_user(db_session, "logo-admin@example.com")
    brand = _reviewable_brand(db_session, user)

    resp = client.patch(
        f"/v1/brands/{brand.id}/profile",
        headers=auth_headers(user),
        json={"logo_url": "https://acme.example/logo.png"},
    )
    assert resp.status_code == 200
    assert resp.json()["logo_url"] == "https://acme.example/logo.png"

    profile = db_session.query(BrandProfile).filter(
        BrandProfile.brand_id == brand.id
    ).first()
    assert profile.logo_url == "https://acme.example/logo.png"


def test_patch_profile_clears_logo_url(
    client: TestClient, db_session: Session
) -> None:
    user = create_user(db_session, "logo-clear@example.com")
    brand = _reviewable_brand(db_session, user)
    profile = db_session.query(BrandProfile).filter(
        BrandProfile.brand_id == brand.id
    ).first()
    profile.logo_url = "https://acme.example/old-logo.png"
    db_session.commit()

    resp = client.patch(
        f"/v1/brands/{brand.id}/profile",
        headers=auth_headers(user),
        json={"logo_url": None},
    )
    assert resp.status_code == 200
    assert resp.json()["logo_url"] is None
