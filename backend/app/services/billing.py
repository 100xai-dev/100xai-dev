"""Razorpay subscription billing + plan-limit enforcement."""

import logging
from datetime import datetime, timezone

import razorpay
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.base import uuid_str
from app.models.billing import Subscription, WebhookEvent
from app.models.core import Organization
from app.models.onboarding import Brand, Job
from app.services.billing_plans import (
    DEFAULT_PLAN_CODE,
    RESOURCE_BLOGS,
    RESOURCE_BRANDS,
    get_plan,
    limit_for,
    razorpay_plan_id,
)

logger = logging.getLogger(__name__)

# Razorpay subscription states that grant access to a paid plan.
ACTIVE_STATES = {"active", "authenticated", "charged", "completed"}
# Total billing cycles to request for a subscription (12 monthly cycles).
DEFAULT_TOTAL_COUNT = 12


class BillingError(Exception):
    """Raised when a billing operation cannot be completed."""


def _client() -> razorpay.Client:
    settings = get_settings()
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise BillingError("Razorpay is not configured (RAZORPAY_KEY_ID/SECRET missing)")
    return razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))


def get_org_subscription(db: Session, org_id: str) -> Subscription | None:
    """Most recent subscription row for an org, if any."""
    return (
        db.query(Subscription)
        .filter(Subscription.org_id == org_id)
        .order_by(Subscription.created_at.desc())
        .first()
    )


def has_active_subscription(db: Session, org_id: str) -> bool:
    """True when the org currently has an active *paid* subscription.

    The webhook promotes ``org.plan_code`` to the paid tier while a subscription
    is active and reverts it to free otherwise, so that is the primary signal.
    We also check the latest subscription row directly as a fallback for the
    window between checkout and the webhook landing.
    """
    org = db.get(Organization, org_id)
    if org and org.plan_code != DEFAULT_PLAN_CODE:
        return True
    sub = get_org_subscription(db, org_id)
    return bool(sub and sub.status in ACTIVE_STATES and sub.plan_code != DEFAULT_PLAN_CODE)


def require_active_subscription(db: Session, org_id: str) -> None:
    """Raise 402 unless the org has an active paid subscription.

    Gates crawling and all content-generation features behind payment: a brand
    new (free) org must subscribe before it can crawl or generate.
    """
    if not has_active_subscription(db, org_id):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": "subscription_required",
                "message": (
                    "An active subscription is required to use this feature. "
                    "Please subscribe to a plan to continue."
                ),
            },
        )


def create_subscription(db: Session, org: Organization, plan_code: str) -> dict:
    """Create a Razorpay subscription for the org and persist a pending row.

    Returns the data the frontend needs to open Razorpay Checkout.
    """
    plan = get_plan(plan_code)
    if plan.code == DEFAULT_PLAN_CODE:
        raise BillingError("Cannot subscribe to the free plan")

    rzp_plan_id = razorpay_plan_id(plan.code)
    if not rzp_plan_id:
        raise BillingError(f"Plan '{plan.code}' has no Razorpay plan id configured")

    client = _client()
    rzp_sub = client.subscription.create({
        "plan_id": rzp_plan_id,
        "total_count": DEFAULT_TOTAL_COUNT,
        "customer_notify": 1,
        "notes": {"org_id": org.id, "plan_code": plan.code},
    })

    sub = Subscription(
        id=uuid_str(),
        org_id=org.id,
        plan_code=plan.code,
        razorpay_subscription_id=rzp_sub["id"],
        razorpay_customer_id=rzp_sub.get("customer_id"),
        status=rzp_sub.get("status", "created"),
    )
    db.add(sub)
    db.commit()

    return {
        "subscription_id": rzp_sub["id"],
        "key_id": get_settings().razorpay_key_id,
        "plan_code": plan.code,
    }


def cancel_subscription(db: Session, org_id: str) -> None:
    sub = get_org_subscription(db, org_id)
    if not sub or not sub.razorpay_subscription_id:
        raise BillingError("No active subscription to cancel")

    client = _client()
    client.subscription.cancel(sub.razorpay_subscription_id, {"cancel_at_cycle_end": 1})
    sub.status = "cancelled"
    db.commit()


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    settings = get_settings()
    if not settings.razorpay_webhook_secret:
        raise BillingError("Razorpay webhook secret is not configured")
    try:
        _client().utility.verify_webhook_signature(
            body.decode("utf-8"),
            signature,
            settings.razorpay_webhook_secret,
        )
        return True
    except razorpay.errors.SignatureVerificationError:
        return False


def handle_event(db: Session, event_id: str, payload: dict) -> None:
    """Idempotently process a Razorpay webhook event."""
    event_type = payload.get("event", "")

    # Idempotency guard: skip events we've already processed.
    if db.query(WebhookEvent).filter(WebhookEvent.razorpay_event_id == event_id).first():
        logger.info("Skipping already-processed Razorpay event %s", event_id)
        return

    sub_entity = (
        payload.get("payload", {})
        .get("subscription", {})
        .get("entity", {})
    )
    rzp_sub_id = sub_entity.get("id")

    sub: Subscription | None = None
    if rzp_sub_id:
        sub = (
            db.query(Subscription)
            .filter(Subscription.razorpay_subscription_id == rzp_sub_id)
            .first()
        )

    if sub:
        new_status = sub_entity.get("status") or sub.status
        sub.status = new_status

        end_ts = sub_entity.get("current_end") or sub_entity.get("charge_at")
        if end_ts:
            sub.current_period_end = datetime.fromtimestamp(int(end_ts), tz=timezone.utc)

        org = db.get(Organization, sub.org_id)
        if org:
            # Promote the org to the paid plan while active; revert to free otherwise.
            org.plan_code = sub.plan_code if new_status in ACTIVE_STATES else DEFAULT_PLAN_CODE

        logger.info("Razorpay event %s updated subscription %s -> %s", event_type, rzp_sub_id, new_status)
    else:
        logger.warning("Razorpay event %s referenced unknown subscription %s", event_type, rzp_sub_id)

    db.add(WebhookEvent(id=uuid_str(), razorpay_event_id=event_id, event_type=event_type))
    db.commit()


def _count_resource(db: Session, org_id: str, resource: str) -> int:
    if resource == RESOURCE_BRANDS:
        return db.query(Brand).filter(Brand.org_id == org_id).count()
    if resource == RESOURCE_BLOGS:
        now = datetime.now(timezone.utc)
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        return (
            db.query(Job)
            .filter(
                Job.org_id == org_id,
                Job.job_type == "content_generation",
                Job.created_at >= month_start,
            )
            .count()
        )
    return 0


def enforce_plan_limit(db: Session, org_id: str, resource: str) -> None:
    """Raise 402 when the org has reached its plan limit for ``resource``."""
    org = db.get(Organization, org_id)
    plan_code = org.plan_code if org else DEFAULT_PLAN_CODE
    limit = limit_for(plan_code, resource)
    if limit < 0:
        return  # unlimited
    current = _count_resource(db, org_id, resource)
    if current >= limit:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": "plan_limit_reached",
                "resource": resource,
                "limit": limit,
                "plan_code": plan_code,
                "message": (
                    f"Your '{plan_code}' plan allows {limit} {resource}. "
                    "Upgrade your plan to continue."
                ),
            },
        )
