import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.jwt import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from app.auth.password import hash_password, validate_password_strength, verify_password
from app.db import get_db
from app.deps import CurrentUser, get_current_user
from app.models.core import EmailVerificationToken, Organization, RefreshToken, User
from app.models.base import uuid_str
from app.schemas.auth import (
    AccessTokenResponse,
    AuthResponse,
    LoginRequest,
    MeResponse,
    MessageResponse,
    OrgOut,
    RefreshRequest,
    ResendVerificationRequest,
    SignupRequest,
    SignupResponse,
    UserOut,
    VerifyEmailRequest,
)
from app.services.email import send_verification_email, send_welcome_email
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _terms_required(user: User) -> bool:
    return user.terms_version_accepted != get_settings().current_terms_version


def _issue_verification_token(user: User, db: Session) -> str:
    """Create a single-use verification token, store its hash, return the raw token."""
    settings = get_settings()
    raw_token = secrets.token_urlsafe(32)
    db.add(EmailVerificationToken(
        id=uuid_str(),
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.email_verification_expiry_hours),
    ))
    return raw_token


def _build_auth_response(user: User, org: Organization, db: Session) -> AuthResponse:
    access_token = create_access_token(user.id, user.org_id, user.role)
    refresh_token = create_refresh_token(user.id, user.org_id, user.role)

    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expiry_days)
    db.add(RefreshToken(
        id=uuid_str(),
        user_id=user.id,
        org_id=user.org_id,
        token_hash=_hash_token(refresh_token),
        expires_at=expires_at,
    ))
    db.commit()

    return AuthResponse(
        user=UserOut.model_validate(user),
        organization=OrgOut.model_validate(org),
        access_token=access_token,
        refresh_token=refresh_token,
        terms_acceptance_required=_terms_required(user),
        terms_current_version=settings.current_terms_version,
    )


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
def signup(
    payload: SignupRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> SignupResponse:
    email = payload.email.lower().strip()

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    try:
        validate_password_strength(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    settings = get_settings()
    now = datetime.now(timezone.utc)

    org = Organization(id=uuid_str(), name=payload.organization_name)
    db.add(org)
    db.flush()

    user = User(
        id=uuid_str(),
        org_id=org.id,
        email=email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        role="admin",
        email_verified=False,
        terms_version_accepted=settings.current_terms_version,
        terms_accepted_at=now,
    )
    db.add(user)
    db.flush()

    raw_token = _issue_verification_token(user, db)
    db.commit()

    # Send the verification email out-of-band so signup isn't blocked on SMTP.
    background_tasks.add_task(send_verification_email, user.email, raw_token)

    return SignupResponse(
        user=UserOut.model_validate(user),
        organization=OrgOut.model_validate(org),
        requires_verification=True,
    )


@router.post("/verify-email", response_model=AuthResponse)
def verify_email(
    payload: VerifyEmailRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> AuthResponse:
    token_hash = _hash_token(payload.token)
    record = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.token_hash == token_hash,
    ).first()

    if (
        not record
        or record.used
        or record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification link is invalid or has expired",
        )

    user = db.get(User, record.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    record.used = True
    if not user.email_verified:
        user.email_verified = True
        user.email_verified_at = datetime.now(timezone.utc)
        background_tasks.add_task(send_welcome_email, user.email)

    org = db.get(Organization, user.org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Organization not found")

    # Auto-login on successful verification.
    return _build_auth_response(user, org, db)


@router.post("/resend-verification", response_model=MessageResponse)
def resend_verification(
    payload: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> MessageResponse:
    # Always return the same message regardless of outcome (no account enumeration).
    generic = MessageResponse(message="If that account exists and is unverified, a new link has been sent.")

    email = payload.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if not user or user.email_verified:
        return generic

    # Invalidate any outstanding tokens, then issue a fresh one.
    db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == user.id,
        EmailVerificationToken.used == False,  # noqa: E712
    ).update({"used": True})
    raw_token = _issue_verification_token(user, db)
    db.commit()

    background_tasks.add_task(send_verification_email, user.email, raw_token)
    return generic


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    email = payload.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "email_not_verified", "email": user.email},
        )

    org = db.get(Organization, user.org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Organization not found")

    return _build_auth_response(user, org, db)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> AccessTokenResponse:
    try:
        claims = decode_refresh_token(payload.refresh_token)
    except TokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    token_hash = _hash_token(payload.refresh_token)
    stored = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked == False,  # noqa: E712
    ).first()

    if not stored or stored.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token invalid or expired")

    # Rotate: revoke old, issue new
    stored.revoked = True
    user = db.get(User, claims["sub"])
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    new_access = create_access_token(user.id, user.org_id, user.role)

    settings = get_settings()
    new_refresh = create_refresh_token(user.id, user.org_id, user.role)
    db.add(RefreshToken(
        id=uuid_str(),
        user_id=user.id,
        org_id=user.org_id,
        token_hash=_hash_token(new_refresh),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expiry_days),
    ))
    db.commit()

    return AccessTokenResponse(access_token=new_access)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshRequest, db: Session = Depends(get_db)) -> None:
    token_hash = _hash_token(payload.refresh_token)
    stored = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if stored:
        stored.revoked = True
        db.commit()


@router.post("/accept-terms", response_model=MessageResponse)
def accept_terms(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    user = db.get(User, current_user.id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.terms_version_accepted = get_settings().current_terms_version
    user.terms_accepted_at = datetime.now(timezone.utc)
    db.commit()
    return MessageResponse(message="Terms accepted")


@router.get("/me", response_model=MeResponse)
def me(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeResponse:
    user = db.get(User, current_user.id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    org = db.get(Organization, user.org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return MeResponse(
        user=UserOut.model_validate(user),
        organization=OrgOut.model_validate(org),
        terms_acceptance_required=_terms_required(user),
        terms_current_version=get_settings().current_terms_version,
    )
