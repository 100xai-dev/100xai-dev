"""Auth endpoint tests: signup, email verification, login, refresh, me, logout."""
import pytest
from fastapi.testclient import TestClient

import app.routers.auth as auth_router
from app.main import app
from app.db import SessionLocal
from app.models.core import EmailVerificationToken, Organization, User, RefreshToken

client = TestClient(app)


def _cleanup(email: str) -> None:
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if user:
        db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
        db.query(EmailVerificationToken).filter(EmailVerificationToken.user_id == user.id).delete()
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
    "accept_terms": True,
}


@pytest.fixture(autouse=True)
def cleanup():
    _cleanup(SIGNUP_PAYLOAD["email"])
    yield
    _cleanup(SIGNUP_PAYLOAD["email"])


@pytest.fixture
def captured_tokens(monkeypatch):
    """Capture verification tokens that would have been emailed."""
    tokens: list[str] = []
    monkeypatch.setattr(auth_router, "send_verification_email", lambda email, token: tokens.append(token))
    monkeypatch.setattr(auth_router, "send_welcome_email", lambda email: None)
    return tokens


def _signup_and_verify(captured_tokens) -> dict:
    """Sign up then verify the email; returns the auth response (with tokens)."""
    client.post("/v1/auth/signup", json=SIGNUP_PAYLOAD)
    verify_res = client.post("/v1/auth/verify-email", json={"token": captured_tokens[-1]})
    assert verify_res.status_code == 200
    return verify_res.json()


def test_signup_requires_verification_and_returns_no_tokens(captured_tokens):
    res = client.post("/v1/auth/signup", json=SIGNUP_PAYLOAD)
    assert res.status_code == 201
    data = res.json()
    assert data["requires_verification"] is True
    assert "access_token" not in data
    assert data["user"]["email"] == SIGNUP_PAYLOAD["email"]
    assert data["user"]["email_verified"] is False
    assert len(captured_tokens) == 1


def test_signup_without_accepting_terms_returns_422():
    payload = {**SIGNUP_PAYLOAD, "accept_terms": False}
    res = client.post("/v1/auth/signup", json=payload)
    assert res.status_code == 422


def test_signup_duplicate_email_returns_409(captured_tokens):
    client.post("/v1/auth/signup", json=SIGNUP_PAYLOAD)
    res = client.post("/v1/auth/signup", json=SIGNUP_PAYLOAD)
    assert res.status_code == 409


def test_signup_weak_password_returns_422():
    payload = {**SIGNUP_PAYLOAD, "password": "weak"}
    res = client.post("/v1/auth/signup", json=payload)
    assert res.status_code == 422


def test_login_before_verification_is_blocked(captured_tokens):
    client.post("/v1/auth/signup", json=SIGNUP_PAYLOAD)
    res = client.post("/v1/auth/login", json={
        "email": SIGNUP_PAYLOAD["email"],
        "password": SIGNUP_PAYLOAD["password"],
    })
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "email_not_verified"


def test_verify_email_logs_in_and_marks_verified(captured_tokens):
    data = _signup_and_verify(captured_tokens)
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["user"]["email_verified"] is True


def test_verify_email_with_bad_token_returns_400(captured_tokens):
    client.post("/v1/auth/signup", json=SIGNUP_PAYLOAD)
    res = client.post("/v1/auth/verify-email", json={"token": "not-a-real-token"})
    assert res.status_code == 400


def test_verify_email_token_is_single_use(captured_tokens):
    client.post("/v1/auth/signup", json=SIGNUP_PAYLOAD)
    token = captured_tokens[-1]
    assert client.post("/v1/auth/verify-email", json={"token": token}).status_code == 200
    assert client.post("/v1/auth/verify-email", json={"token": token}).status_code == 400


def test_resend_verification_is_generic_and_issues_token(captured_tokens):
    client.post("/v1/auth/signup", json=SIGNUP_PAYLOAD)
    res = client.post("/v1/auth/resend-verification", json={"email": SIGNUP_PAYLOAD["email"]})
    assert res.status_code == 200
    assert "message" in res.json()
    assert len(captured_tokens) == 2  # one from signup, one from resend


def test_resend_for_unknown_email_is_generic(captured_tokens):
    res = client.post("/v1/auth/resend-verification", json={"email": "nobody@example.com"})
    assert res.status_code == 200


def test_login_after_verification_returns_tokens(captured_tokens):
    _signup_and_verify(captured_tokens)
    res = client.post("/v1/auth/login", json={
        "email": SIGNUP_PAYLOAD["email"],
        "password": SIGNUP_PAYLOAD["password"],
    })
    assert res.status_code == 200
    assert res.json()["access_token"]


def test_login_wrong_password_returns_401(captured_tokens):
    _signup_and_verify(captured_tokens)
    res = client.post("/v1/auth/login", json={
        "email": SIGNUP_PAYLOAD["email"],
        "password": "WrongPass1!",
    })
    assert res.status_code == 401


def test_me_returns_user(captured_tokens):
    token = _signup_and_verify(captured_tokens)["access_token"]
    res = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    body = res.json()
    assert body["user"]["email"] == SIGNUP_PAYLOAD["email"]
    assert body["terms_acceptance_required"] is False


def test_refresh_rotates_token(captured_tokens):
    refresh_token = _signup_and_verify(captured_tokens)["refresh_token"]
    res = client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert res.status_code == 200
    assert res.json()["access_token"]


def test_logout_revokes_refresh_token(captured_tokens):
    refresh_token = _signup_and_verify(captured_tokens)["refresh_token"]
    logout_res = client.post("/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout_res.status_code == 204
    res = client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert res.status_code == 401
