"""Razorpay billing: plans, subscribe, webhook idempotency, plan limits."""
import pytest

from app.models.base import uuid_str
from app.models.billing import Subscription, WebhookEvent
from app.models.core import Organization
from app.services import billing
from tests.conftest import auth_headers, create_user


class FakeSubscriptionApi:
    def create(self, data):
        return {"id": "sub_test123", "status": "created", "customer_id": "cust_test"}

    def cancel(self, sub_id, data):
        return {"id": sub_id, "status": "cancelled"}


class FakeClient:
    def __init__(self):
        self.subscription = FakeSubscriptionApi()


@pytest.fixture
def fake_razorpay(monkeypatch):
    monkeypatch.setattr(billing, "_client", lambda: FakeClient())
    monkeypatch.setattr(billing, "razorpay_plan_id", lambda code: "plan_fake")


def test_list_plans_is_public(client):
    res = client.get("/v1/billing/plans")
    assert res.status_code == 200
    codes = {p["code"] for p in res.json()["plans"]}
    assert {"free", "starter", "pro"} <= codes


def test_subscription_defaults_to_free(client, db_session):
    user = create_user(db_session, "bill_a@example.com")
    res = client.get("/v1/billing/subscription", headers=auth_headers(user))
    assert res.status_code == 200
    body = res.json()
    assert body["plan_code"] == "free"
    assert body["subscription"] is None


def test_subscribe_creates_subscription(client, db_session, fake_razorpay):
    user = create_user(db_session, "bill_b@example.com")
    res = client.post(
        "/v1/billing/subscribe",
        json={"plan_code": "starter"},
        headers=auth_headers(user),
    )
    assert res.status_code == 200
    assert res.json()["subscription_id"] == "sub_test123"

    sub = db_session.query(Subscription).filter(Subscription.org_id == user.org_id).first()
    assert sub is not None
    assert sub.plan_code == "starter"
    assert sub.razorpay_subscription_id == "sub_test123"


def test_subscribe_to_free_is_rejected(client, db_session, fake_razorpay):
    user = create_user(db_session, "bill_c@example.com")
    res = client.post(
        "/v1/billing/subscribe",
        json={"plan_code": "free"},
        headers=auth_headers(user),
    )
    assert res.status_code == 400


def test_webhook_activates_subscription_and_is_idempotent(client, db_session, monkeypatch):
    user = create_user(db_session, "bill_d@example.com")
    db_session.add(Subscription(
        id=uuid_str(),
        org_id=user.org_id,
        plan_code="pro",
        razorpay_subscription_id="sub_webhook1",
        status="created",
    ))
    db_session.commit()

    monkeypatch.setattr(billing, "verify_webhook_signature", lambda body, sig: True)

    payload = {
        "event": "subscription.activated",
        "payload": {"subscription": {"entity": {"id": "sub_webhook1", "status": "active"}}},
    }
    headers = {"X-Razorpay-Signature": "sig", "X-Razorpay-Event-Id": "evt_1"}

    res = client.post("/v1/billing/webhook", json=payload, headers=headers)
    assert res.status_code == 200

    db_session.expire_all()
    org = db_session.get(Organization, user.org_id)
    assert org.plan_code == "pro"
    sub = db_session.query(Subscription).filter_by(razorpay_subscription_id="sub_webhook1").first()
    assert sub.status == "active"

    # Re-deliver the same event id -> no duplicate processing.
    res2 = client.post("/v1/billing/webhook", json=payload, headers=headers)
    assert res2.status_code == 200
    db_session.expire_all()
    assert db_session.query(WebhookEvent).filter_by(razorpay_event_id="evt_1").count() == 1


def test_enforce_plan_limit_blocks_over_quota(db_session):
    from fastapi import HTTPException

    from app.models.onboarding import Brand
    from app.services.billing import enforce_plan_limit
    from app.services.billing_plans import RESOURCE_BRANDS

    user = create_user(db_session, "bill_e@example.com")
    # Free plan allows 1 brand; create one so the next is over quota.
    db_session.add(Brand(
        id="brand-1",
        org_id=user.org_id,
        name="B1",
        status="DRAFT",
        dna_source="manual",
        created_by=user.id,
    ))
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        enforce_plan_limit(db_session, user.org_id, RESOURCE_BRANDS)
    assert exc.value.status_code == 402


def test_create_brand_requires_active_subscription(client, db_session):
    """A free (unpaid) org cannot create a brand / trigger a crawl."""
    user = create_user(db_session, "gated@example.com")  # defaults to free plan
    res = client.post(
        "/v1/brands",
        headers=auth_headers(user),
        json={"name": "Gated Brand", "dna_source": "manual"},
    )
    assert res.status_code == 402
    assert res.json()["detail"]["code"] == "subscription_required"


def test_paid_org_can_create_brand(client, db_session):
    """An org on a paid plan passes the subscription gate."""
    user = create_user(db_session, "paid@example.com", plan_code="pro")
    res = client.post(
        "/v1/brands",
        headers=auth_headers(user),
        json={"name": "Paid Brand", "dna_source": "manual"},
    )
    assert res.status_code == 201


def test_has_active_subscription_reflects_subscription_row(db_session):
    """A free-plan org with an active subscription row still counts as paid."""
    from app.models.billing import Subscription

    user = create_user(db_session, "sub_row@example.com")  # plan_code stays free
    assert billing.has_active_subscription(db_session, user.org_id) is False

    db_session.add(Subscription(
        id=uuid_str(),
        org_id=user.org_id,
        plan_code="pro",
        razorpay_subscription_id="sub_active1",
        status="active",
    ))
    db_session.commit()
    assert billing.has_active_subscription(db_session, user.org_id) is True
