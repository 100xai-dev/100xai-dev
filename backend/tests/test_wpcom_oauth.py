"""Tests for the WordPress.com OAuth connect flow (W3)."""

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import IntegrationAccount, IntegrationToken
from app.models.onboarding import Brand
from app.routers import wpcom_oauth
from tests.conftest import auth_headers, create_user


@pytest.fixture()
def wpcom_settings(monkeypatch: pytest.MonkeyPatch):
    get_settings.cache_clear()
    s = get_settings()
    monkeypatch.setattr(s, "wpcom_client_id", "test-client", raising=False)
    monkeypatch.setattr(s, "wpcom_client_secret", "test-secret", raising=False)
    monkeypatch.setattr(s, "token_encryption_key", Fernet.generate_key().decode(), raising=False)
    yield s
    get_settings.cache_clear()


def _brand(db: Session, user) -> Brand:
    brand = Brand(org_id=user.org_id, name="Acme", website_url="https://acme.example",
                  dna_source="manual", status="READY", created_by=user.id)
    db.add(brand)
    db.commit()
    return brand


def test_start_returns_authorize_url(client: TestClient, db_session: Session, wpcom_settings) -> None:
    user = create_user(db_session, "wpcom-start@example.com")
    brand = _brand(db_session, user)

    resp = client.get(f"/v1/integrations/wordpress/oauth/start?brand_id={brand.id}", headers=auth_headers(user))
    assert resp.status_code == 200
    url = resp.json()["authorize_url"]
    assert url.startswith("https://public-api.wordpress.com/oauth2/authorize")
    assert "client_id=test-client" in url
    assert "state=" in url


def test_callback_persists_oauth_integration(
    client: TestClient, db_session: Session, wpcom_settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = create_user(db_session, "wpcom-cb@example.com")
    brand = _brand(db_session, user)
    state = wpcom_oauth._mint_state(brand.id, user.org_id, user.id)

    class _FakeResp:
        status_code = 200
        text = ""
        def json(self):
            return {"access_token": "tok_abc", "blog_id": 12345, "blog_url": "https://acme.wordpress.com"}

    class _FakeClient:
        def __init__(self, *a, **k): ...
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, *a, **k): return _FakeResp()

    monkeypatch.setattr(wpcom_oauth.httpx, "AsyncClient", _FakeClient)

    resp = client.get(
        f"/v1/integrations/wordpress/oauth/callback?code=abc&state={state}",
        follow_redirects=False,
    )
    assert resp.status_code in (302, 307)
    assert "wpcom_connected=1" in resp.headers["location"]

    account = db_session.query(IntegrationAccount).filter_by(brand_id=brand.id, provider="wordpress").one()
    assert account.status == "active"
    assert account.config["auth_type"] == "oauth"
    assert account.config["blog_id"] == "12345"
    token = db_session.query(IntegrationToken).filter_by(integration_account_id=account.id).one()
    assert token.encrypted_payload  # credentials stored encrypted, not plaintext


def test_callback_rejects_bad_state(client: TestClient, db_session: Session, wpcom_settings) -> None:
    resp = client.get(
        "/v1/integrations/wordpress/oauth/callback?code=abc&state=not-a-real-token",
        follow_redirects=False,
    )
    assert resp.status_code == 400
