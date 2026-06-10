"""Versioned Terms & Conditions acceptance."""
from tests.conftest import auth_headers, create_user


def test_me_flags_terms_required_when_not_accepted(client, db_session):
    user = create_user(db_session, "terms_a@example.com")
    # create_user does not record terms acceptance -> re-acceptance required.
    res = client.get("/v1/auth/me", headers=auth_headers(user))
    assert res.status_code == 200
    assert res.json()["terms_acceptance_required"] is True


def test_accept_terms_clears_requirement(client, db_session):
    user = create_user(db_session, "terms_b@example.com")
    headers = auth_headers(user)

    accept = client.post("/v1/auth/accept-terms", headers=headers)
    assert accept.status_code == 200

    res = client.get("/v1/auth/me", headers=headers)
    assert res.json()["terms_acceptance_required"] is False
    assert res.json()["terms_current_version"] is not None
