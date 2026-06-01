"""Auth endpoint tests: signup, login, refresh, me, logout."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db import SessionLocal
from app.models.core import Organization, User, RefreshToken

client = TestClient(app)


def _cleanup(email: str) -> None:
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if user:
        db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
        org = db.get(Organization, user.org_id)
        db.delete(user)
        if org:
            db.delete(org)
        db.commit()
    db.close()


SIGNUP_PAYLOAD = {
    "name": "Test User",
    "email": "authtest_unique@example.com",
    "password": "Test1234!",
    "organization_name": "Test Org",
}


@pytest.fixture(autouse=True)
def cleanup():
    _cleanup(SIGNUP_PAYLOAD["email"])
    yield
    _cleanup(SIGNUP_PAYLOAD["email"])


def test_signup_creates_user_and_returns_tokens():
    res = client.post("/v1/auth/signup", json=SIGNUP_PAYLOAD)
    assert res.status_code == 201
    data = res.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["user"]["email"] == SIGNUP_PAYLOAD["email"]
    assert data["user"]["role"] == "admin"
    assert data["organization"]["name"] == SIGNUP_PAYLOAD["organization_name"]


def test_signup_duplicate_email_returns_409():
    client.post("/v1/auth/signup", json=SIGNUP_PAYLOAD)
    res = client.post("/v1/auth/signup", json=SIGNUP_PAYLOAD)
    assert res.status_code == 409


def test_signup_weak_password_returns_422():
    payload = {**SIGNUP_PAYLOAD, "password": "weak"}
    res = client.post("/v1/auth/signup", json=payload)
    assert res.status_code == 422


def test_login_returns_tokens():
    client.post("/v1/auth/signup", json=SIGNUP_PAYLOAD)
    res = client.post("/v1/auth/login", json={
        "email": SIGNUP_PAYLOAD["email"],
        "password": SIGNUP_PAYLOAD["password"],
    })
    assert res.status_code == 200
    data = res.json()
    assert data["access_token"]
    assert data["refresh_token"]


def test_login_wrong_password_returns_401():
    client.post("/v1/auth/signup", json=SIGNUP_PAYLOAD)
    res = client.post("/v1/auth/login", json={
        "email": SIGNUP_PAYLOAD["email"],
        "password": "WrongPass1!",
    })
    assert res.status_code == 401


def test_me_returns_user():
    signup_res = client.post("/v1/auth/signup", json=SIGNUP_PAYLOAD)
    token = signup_res.json()["access_token"]
    res = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["user"]["email"] == SIGNUP_PAYLOAD["email"]


def test_refresh_rotates_token():
    signup_res = client.post("/v1/auth/signup", json=SIGNUP_PAYLOAD)
    refresh_token = signup_res.json()["refresh_token"]
    res = client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert res.status_code == 200
    assert res.json()["access_token"]


def test_logout_revokes_refresh_token():
    signup_res = client.post("/v1/auth/signup", json=SIGNUP_PAYLOAD)
    refresh_token = signup_res.json()["refresh_token"]
    logout_res = client.post("/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout_res.status_code == 204
    res = client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert res.status_code == 401
