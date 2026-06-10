from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, utcnow, uuid_str


class Subscription(Base, TimestampMixin):
    """A Razorpay recurring subscription owned by an organization."""

    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_str)
    org_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("organizations.id"), nullable=False)
    plan_code: Mapped[str] = mapped_column(String, nullable=False)
    razorpay_subscription_id: Mapped[str | None] = mapped_column(String, unique=True)
    razorpay_customer_id: Mapped[str | None] = mapped_column(String)
    # created | authenticated | active | pending | halted | cancelled | completed | expired
    status: Mapped[str] = mapped_column(String, nullable=False, default="created")
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WebhookEvent(Base):
    """Records processed Razorpay webhook events for idempotency."""

    __tablename__ = "webhook_events"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_str)
    razorpay_event_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
