"""Tests for the brand persona model and API."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.onboarding import Brand
from app.models.persona import BrandPersona
from tests.conftest import auth_headers, create_user


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
    db.commit()
    return brand


def test_brand_persona_model_persists(db_session: Session) -> None:
    user = create_user(db_session, "persona-model@example.com")
    brand = _brand(db_session, user)

    persona = BrandPersona(
        brand_id=brand.id,
        name="Acme",
        domain="acme.example",
        url="https://acme.example",
        one_liner="We make robots.",
        audience="Warehouse operators",
        tone_tags=["Bold", "Warm"],
        founder_name="Ada Lovelace",
        founder_role="Founder & CEO",
        mission="Zero downtime warehouses",
        accent_color="#F58000",
    )
    db_session.add(persona)
    db_session.commit()

    fetched = db_session.query(BrandPersona).filter(
        BrandPersona.brand_id == brand.id
    ).first()
    assert fetched is not None
    assert fetched.tone_tags == ["Bold", "Warm"]
    assert fetched.accent_color == "#F58000"
    assert fetched.created_at is not None