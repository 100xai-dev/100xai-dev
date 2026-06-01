import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
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
from app.models.core import Organization, RefreshToken, User
from app.models.base import uuid_str
from app.schemas.auth import (
    AccessTokenResponse,
    AuthResponse,
    LoginRequest,
    MeResponse,
    OrgOut,
    RefreshRequest,
    SignupRequest,
    UserOut,
)
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


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
    )


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> AuthResponse:
    email = payload.email.lower().strip()

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    try:
        validate_password_strength(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

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
    )
    db.add(user)
    db.flush()

    return _build_auth_response(user, org, db)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    email = payload.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
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
    return MeResponse(user=UserOut.model_validate(user), organization=OrgOut.model_validate(org))
