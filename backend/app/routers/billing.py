import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import CurrentUser, get_current_user
from app.models.core import Organization
from app.services import billing
from app.services.billing_plans import get_plan, public_catalog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


class SubscribeRequest(BaseModel):
    plan_code: str


@router.get("/plans")
def list_plans() -> dict:
    return {"plans": public_catalog()}


@router.get("/subscription")
def get_subscription(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    org = db.get(Organization, current_user.org_id)
    plan = get_plan(org.plan_code if org else None)
    sub = billing.get_org_subscription(db, current_user.org_id)
    return {
        "plan_code": plan.code,
        "plan_name": plan.name,
        "limits": plan.limits,
        "subscription": None if not sub else {
            "status": sub.status,
            "plan_code": sub.plan_code,
            "razorpay_subscription_id": sub.razorpay_subscription_id,
            "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
        },
    }


@router.post("/subscribe")
def subscribe(
    payload: SubscribeRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    org = db.get(Organization, current_user.org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    try:
        return billing.create_subscription(db, org, payload.plan_code)
    except billing.BillingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/cancel", status_code=status.HTTP_204_NO_CONTENT)
def cancel(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    try:
        billing.cancel_subscription(db, current_user.org_id)
    except billing.BillingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    """Razorpay webhook receiver. No auth — verified via signature header."""
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    try:
        if not billing.verify_webhook_signature(body, signature):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")
    except billing.BillingError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    payload = await request.json()
    # Razorpay sends a unique event id in this header; fall back to a composite key.
    event_id = request.headers.get("X-Razorpay-Event-Id") or f"{payload.get('event')}:{payload.get('created_at')}"
    billing.handle_event(db, event_id, payload)
    return {"status": "ok"}
