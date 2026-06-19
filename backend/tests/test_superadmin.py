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


from app.models import AuditLog, Brand


def test_list_organizations_returns_counts(db_session):
    from app.services.superadmin import list_organizations
    u = create_user(db_session, "counts@acme.test", role="admin")
    db_session.add(Brand(org_id=u.org_id, name="B1", dna_source="manual", status="DRAFT", created_by=u.id))
    db_session.commit()

    items = list_organizations(db_session)
    row = next(i for i in items if i.id == u.org_id)
    assert row.user_count == 1
    assert row.brand_count == 1
    assert row.status == "active"


def test_create_organization_creates_org_admin_and_token(db_session, monkeypatch):
    import app.services.superadmin as svc
    sent = []
    monkeypatch.setattr(svc, "send_verification_email", lambda email, token: sent.append((email, token)))

    from app.schemas.superadmin import CreateOrgRequest
    from app.models import EmailVerificationToken, Organization, User

    actor = "superadmin-id"
    resp = svc.create_organization(
        db_session,
        CreateOrgRequest(organization_name="NewCo", plan_code="starter",
                         admin_name="Ann", admin_email="ann@example.com"),
        actor_user_id=actor,
    )
    org = db_session.get(Organization, resp.org_id)
    assert org.name == "NewCo" and org.plan_code == "starter"
    admin = db_session.get(User, resp.admin_user_id)
    assert admin.role == "admin" and admin.email == "ann@example.com" and admin.email_verified is False
    assert db_session.query(EmailVerificationToken).filter_by(user_id=admin.id).count() == 1
    assert len(sent) == 1
    assert db_session.query(AuditLog).filter_by(org_id=org.id, action="superadmin.org.created").count() == 1


def test_set_org_status_suspends_and_audits(db_session):
    from app.services.superadmin import set_org_status
    u = create_user(db_session, "tosuspend@acme.test", role="admin")
    set_org_status(db_session, u.org_id, "suspended", actor_user_id="root")
    from app.models import Organization
    assert db_session.get(Organization, u.org_id).status == "suspended"
    assert db_session.query(AuditLog).filter_by(org_id=u.org_id, action="superadmin.org.suspended").count() == 1


def test_delete_organization_soft_deletes_and_hides(db_session):
    from app.services.superadmin import delete_organization, list_organizations
    from app.models import Organization
    u = create_user(db_session, "todelete@acme.test", role="admin")
    org_id = u.org_id
    delete_organization(db_session, org_id, actor_user_id="root")
    org = db_session.get(Organization, org_id)
    assert org is not None and org.status == "deleted"
    # Soft-deleted orgs are hidden from the superadmin list.
    assert all(i.id != org_id for i in list_organizations(db_session))
