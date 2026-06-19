from app.models import Organization, User


def test_seed_creates_and_is_idempotent(db_session, monkeypatch):
    import app.scripts.seed_superadmins as seed

    class FakeSettings:
        superadmin_emails = "root@platform.test, ops@platform.test"
        superadmin_password = "Bootstrap123!"

    monkeypatch.setattr(seed, "get_settings", lambda: FakeSettings())

    seed.seed_superadmins(db_session)
    users = db_session.query(User).filter(User.role == "superadmin").all()
    assert {u.email for u in users} == {"root@platform.test", "ops@platform.test"}
    assert all(u.email_verified for u in users)
    system_orgs = db_session.query(Organization).filter(Organization.name == seed.SYSTEM_ORG_NAME).count()
    assert system_orgs == 1

    # Re-run: no duplicates.
    seed.seed_superadmins(db_session)
    assert db_session.query(User).filter(User.role == "superadmin").count() == 2
    assert db_session.query(Organization).filter(Organization.name == seed.SYSTEM_ORG_NAME).count() == 1


def test_seed_promotes_existing_user(db_session, monkeypatch):
    import app.scripts.seed_superadmins as seed
    from tests.conftest import create_user

    existing = create_user(db_session, "promote@platform.test", role="admin")

    class FakeSettings:
        superadmin_emails = "promote@platform.test"
        superadmin_password = "Bootstrap123!"

    monkeypatch.setattr(seed, "get_settings", lambda: FakeSettings())
    seed.seed_superadmins(db_session)
    db_session.refresh(existing)
    assert existing.role == "superadmin" and existing.email_verified is True
