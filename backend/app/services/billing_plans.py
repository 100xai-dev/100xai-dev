"""Subscription plan catalog.

Plans are defined in code (not the DB) so they are easy to read and version.
Prices are placeholders in INR (paise are used by Razorpay, but we only display
the rupee value here). The per-tier Razorpay ``plan_id`` is read from settings,
so a plan is only "subscribable" once its Razorpay plan id is configured.

Limits are enforced by ``app.services.billing.enforce_plan_limit``.
"""

from dataclasses import dataclass

from app.config import get_settings


@dataclass(frozen=True)
class Plan:
    code: str
    name: str
    price_inr: int  # monthly, in rupees (placeholder values)
    limits: dict[str, int]  # resource -> max count (-1 = unlimited)


# Resource keys used by enforce_plan_limit / the frontend.
RESOURCE_BRANDS = "brands"
RESOURCE_BLOGS = "blogs"  # blogs per calendar month

PLANS: dict[str, Plan] = {
    "free": Plan("free", "Free", 0, {RESOURCE_BRANDS: 1, RESOURCE_BLOGS: 3}),
    "starter": Plan("starter", "Starter", 999, {RESOURCE_BRANDS: 3, RESOURCE_BLOGS: 30}),
    "pro": Plan("pro", "Pro", 2999, {RESOURCE_BRANDS: 10, RESOURCE_BLOGS: 150}),
}

DEFAULT_PLAN_CODE = "free"


def get_plan(code: str | None) -> Plan:
    return PLANS.get(code or DEFAULT_PLAN_CODE, PLANS[DEFAULT_PLAN_CODE])


def limit_for(plan_code: str | None, resource: str) -> int:
    """Return the limit for a resource under a plan (-1 = unlimited, default 0)."""
    return get_plan(plan_code).limits.get(resource, 0)


def razorpay_plan_id(plan_code: str) -> str | None:
    """Map a plan code to its configured Razorpay plan_id (None for free/unset)."""
    settings = get_settings()
    return {
        "starter": settings.razorpay_plan_starter,
        "pro": settings.razorpay_plan_pro,
    }.get(plan_code)


def public_catalog() -> list[dict]:
    """Serializable plan catalog for the frontend."""
    return [
        {
            "code": p.code,
            "name": p.name,
            "price_inr": p.price_inr,
            "limits": p.limits,
            "subscribable": p.code != DEFAULT_PLAN_CODE and razorpay_plan_id(p.code) is not None,
        }
        for p in PLANS.values()
    ]
