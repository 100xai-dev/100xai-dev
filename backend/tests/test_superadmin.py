from app.auth.password import hash_password
from app.models import Organization, User
from app.models.base import uuid_str
from tests.conftest import auth_headers, create_user


def _make_login_user(db, email="login@example.com", password="Test1234!"):
    org = Organization(id=uuid_str(), name="LoginOrg", plan_code="free")
    db.add(org)
    db.flush()
    user = User(
        id=uuid_str(), org_id=org.id, email=email, password_hash=hash_password(password),
        name="Login", role="admin", email_verified=True,
    )
    db.add(user)
    db.commit()
    return org, user


def test_login_blocked_when_org_suspended(client, db_session):
    org, user = _make_login_user(db_session, "susp@example.com")
    org.status = "suspended"
    db_session.commit()
    res = client.post("/v1/auth/login", json={"email": "susp@example.com", "password": "Test1234!"})
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "org_suspended"


def test_login_blocked_when_user_disabled(client, db_session):
    org, user = _make_login_user(db_session, "dis@example.com")
    user.disabled = True
    db_session.commit()
    res = client.post("/v1/auth/login", json={"email": "dis@example.com", "password": "Test1234!"})
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "account_disabled"


def test_login_blocked_when_org_deleted(client, db_session):
    org, user = _make_login_user(db_session, "del@example.com")
    org.status = "deleted"
    db_session.commit()
    res = client.post("/v1/auth/login", json={"email": "del@example.com", "password": "Test1234!"})
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "org_deleted"


def test_login_succeeds_when_active(client, db_session):
    _make_login_user(db_session, "ok@example.com")
    res = client.post("/v1/auth/login", json={"email": "ok@example.com", "password": "Test1234!"})
    assert res.status_code == 200
    assert "access_token" in res.json()
