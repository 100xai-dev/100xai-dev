"""Idempotently provision platform superadmins from settings.

Run as a one-off:  python -m app.scripts.seed_superadmins
Reads SUPERADMIN_EMAILS (comma-separated) and optional SUPERADMIN_PASSWORD.
Each listed email is created (in a dedicated system org) or promoted to the
`superadmin` role and marked email-verified. New users without a configured
password get a random one printed once for the operator to copy.
"""

import logging
import secrets
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.auth.password import hash_password
from app.config import get_settings
from app.db import SessionLocal
from app.models import Organization, User
from app.models.base import uuid_str

logger = logging.getLogger(__name__)

SYSTEM_ORG_NAME = "__platform__"


def _get_or_create_system_org(db: Session) -> Organization:
    org = db.query(Organization).filter(Organization.name == SYSTEM_ORG_NAME).first()
    if org is None:
        org = Organization(id=uuid_str(), name=SYSTEM_ORG_NAME, plan_code="free")
        db.add(org)
        db.flush()
    return org


def seed_superadmins(db: Session) -> None:
    settings = get_settings()
    emails = [e.strip().lower() for e in (settings.superadmin_emails or "").split(",") if e.strip()]
    if not emails:
        logger.warning("SUPERADMIN_EMAILS is empty; nothing to seed.")
        return

    system_org = _get_or_create_system_org(db)

    for email in emails:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            password = settings.superadmin_password or secrets.token_urlsafe(16)
            user = User(
                id=uuid_str(), org_id=system_org.id, email=email,
                password_hash=hash_password(password), name=email.split("@")[0],
                role="superadmin", email_verified=True,
                email_verified_at=datetime.now(timezone.utc),
            )
            db.add(user)
            if not settings.superadmin_password:
                logger.info("Created superadmin %s with generated password: %s", email, password)
        else:
            user.role = "superadmin"
            user.email_verified = True
            if user.email_verified_at is None:
                user.email_verified_at = datetime.now(timezone.utc)
            user.disabled = False
    db.commit()
    logger.info("Seeded %d superadmin(s).", len(emails))


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    db = SessionLocal()
    try:
        seed_superadmins(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
