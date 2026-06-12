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


def test_get_persona_404_when_absent(client: TestClient, db_session: Session) -> None:
    user = create_user(db_session, "persona-get-404@example.com")
    brand = _brand(db_session, user)

    resp = client.get(f"/v1/brands/{brand.id}/persona", headers=auth_headers(user))
    assert resp.status_code == 404


def test_put_persona_creates_then_get_returns_it(
    client: TestClient, db_session: Session
) -> None:
    user = create_user(db_session, "persona-put@example.com")
    brand = _brand(db_session, user)

    body = {
        "name": "Acme",
        "domain": "acme.example",
        "url": "https://acme.example",
        "one_liner": "We make robots.",
        "audience": "Warehouse operators",
        "tone_tags": ["Bold", "Warm"],
        "founder_name": "Ada Lovelace",
        "founder_role": "Founder & CEO",
        "mission": "Zero downtime warehouses",
        "accent_color": "#F58000",
    }
    put = client.put(f"/v1/brands/{brand.id}/persona", headers=auth_headers(user), json=body)
    assert put.status_code == 200
    assert put.json()["tone_tags"] == ["Bold", "Warm"]
    assert put.json()["brand_id"] == brand.id

    got = client.get(f"/v1/brands/{brand.id}/persona", headers=auth_headers(user))
    assert got.status_code == 200
    assert got.json()["founder_name"] == "Ada Lovelace"
    assert got.json()["one_liner"] == "We make robots."


def test_put_persona_upserts_in_place(client: TestClient, db_session: Session) -> None:
    user = create_user(db_session, "persona-upsert@example.com")
    brand = _brand(db_session, user)

    client.put(
        f"/v1/brands/{brand.id}/persona",
        headers=auth_headers(user),
        json={"name": "Acme", "one_liner": "v1", "tone_tags": ["Bold"]},
    )
    client.put(
        f"/v1/brands/{brand.id}/persona",
        headers=auth_headers(user),
        json={"name": "Acme", "one_liner": "v2", "tone_tags": ["Warm", "Playful"]},
    )

    personas = db_session.query(BrandPersona).filter(
        BrandPersona.brand_id == brand.id
    ).all()
    assert len(personas) == 1
    assert personas[0].one_liner == "v2"
    assert personas[0].tone_tags == ["Warm", "Playful"]


def test_persona_scoped_to_org(client: TestClient, db_session: Session) -> None:
    owner = create_user(db_session, "persona-owner@example.com")
    brand = _brand(db_session, owner)
    client.put(
        f"/v1/brands/{brand.id}/persona",
        headers=auth_headers(owner),
        json={"name": "Acme"},
    )

    outsider = create_user(db_session, "persona-outsider@example.com")
    # Outsider is in a different org → must not see the brand or its persona.
    resp = client.get(f"/v1/brands/{brand.id}/persona", headers=auth_headers(outsider))
    assert resp.status_code == 404