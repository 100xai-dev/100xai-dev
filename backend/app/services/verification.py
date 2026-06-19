import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import EmailVerificationToken
from app.models.base import uuid_str


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_verification_token(db: Session, user_id: str) -> str:
    """Create a single-use email-verification token, store its hash, return the raw token.

    Does not commit — the caller commits as part of its own transaction.
    """
    settings = get_settings()
    raw_token = secrets.token_urlsafe(32)
    db.add(EmailVerificationToken(
        id=uuid_str(),
        user_id=user_id,
        token_hash=hash_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.email_verification_expiry_hours),
    ))
    return raw_token
