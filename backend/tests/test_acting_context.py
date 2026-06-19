import pytest

from app.auth.rbac import require_role
from app.models import Brand
from fastapi import HTTPException
from tests.conftest import auth_headers, create_user


def test_require_role_allows_superadmin_for_any_set():
    # Should not raise even though "superadmin" is not in the allowed set.
    require_role("superadmin", {"admin"})
    require_role("superadmin", {"viewer"})


def test_require_role_still_blocks_unlisted_normal_role():
    with pytest.raises(HTTPException) as exc:
        require_role("viewer", {"admin"})
    assert exc.value.status_code == 403


def test_superadmin_acting_header_scopes_to_target_org(client, db_session):
    target = create_user(db_session, "owner@acme.test", role="admin")
    superadmin = create_user(db_session, "root@platform.test", role="superadmin")

    # Seed a brand in the TARGET org so we can prove the response is scoped
    # to that org, not to the superadmin's own (empty) org.
    db_session.add(Brand(org_id=target.org_id, name="TargetBrand", dna_source="manual", status="DRAFT", created_by=target.id))
    db_session.commit()

    headers = auth_headers(superadmin)
    headers["X-Acting-Org-Id"] = target.org_id

    res = client.get("/v1/brands", headers=headers)
    assert res.status_code == 200
    assert "TargetBrand" in [b["name"] for b in res.json()["items"]]


def test_acting_header_ignored_for_non_superadmin(client, db_session):
    victim = create_user(db_session, "victim@acme.test", role="admin")
    attacker = create_user(db_session, "attacker@evil.test", role="admin")

    headers = auth_headers(attacker)
    headers["X-Acting-Org-Id"] = victim.org_id

    # The header must be ignored: attacker stays scoped to their own org.
    # Create a brand as the victim, then confirm the attacker cannot see it.
    brand = Brand(org_id=victim.org_id, name="Secret", dna_source="manual", status="DRAFT", created_by=victim.id)
    db_session.add(brand)
    db_session.commit()

    res = client.get("/v1/brands", headers=headers)
    assert res.status_code == 200
    names = [b["name"] for b in res.json()["items"]]
    assert "Secret" not in names


def test_superadmin_acting_on_unknown_org_returns_404(client, db_session):
    superadmin = create_user(db_session, "root2@platform.test", role="superadmin")
    headers = auth_headers(superadmin)
    headers["X-Acting-Org-Id"] = "00000000-0000-0000-0000-000000000000"
    res = client.get("/v1/brands", headers=headers)
    assert res.status_code == 404
