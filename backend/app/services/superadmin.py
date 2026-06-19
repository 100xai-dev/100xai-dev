import hashlib
import secrets

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Brand,
    EmailVerificationToken,
    Organization,
    User,
)
from app.models.base import uuid_str
from app.schemas.superadmin import (
    CreateOrgRequest,
    CreateOrgResponse,
    CreateOrgUserRequest,
    OrgListItem,
    UpdateOrgRequest,
    UpdateOrgUserRequest,
)
from app.services.audit import write_audit
from app.services.billing_plans import PLANS
from app.services.email import send_verification_email
from app.services.verification import issue_verification_token


def _require_org(db: Session, org_id: str) -> Organization:
    org = db.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="organization not found")
    return org


def list_organizations(db: Session) -> list[OrgListItem]:
    user_counts = dict(
        db.execute(select(User.org_id, func.count(User.id)).group_by(User.org_id)).all()
    )
    brand_counts = dict(
        db.execute(select(Brand.org_id, func.count(Brand.id)).group_by(Brand.org_id)).all()
    )
    orgs = db.execute(
        select(Organization).where(Organization.status != "deleted").order_by(Organization.name)
    ).scalars().all()
    return [
        OrgListItem(
            id=o.id,
            name=o.name,
            plan_code=o.plan_code,
            status=o.status,
            user_count=user_counts.get(o.id, 0),
            brand_count=brand_counts.get(o.id, 0),
        )
        for o in orgs
    ]


def create_organization(db: Session, payload: CreateOrgRequest, actor_user_id: str) -> CreateOrgResponse:
    if payload.plan_code not in PLANS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="unknown plan_code")

    email = payload.admin_email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    org = Organization(id=uuid_str(), name=payload.organization_name.strip(), plan_code=payload.plan_code)
    db.add(org)
    db.flush()

    # Not a usable password: this value is never verified — the admin sets a real password via the invite/verification flow.
    placeholder_hash = hashlib.sha256(secrets.token_urlsafe(32).encode()).hexdigest()
    admin = User(
        id=uuid_str(),
        org_id=org.id,
        email=email,
        password_hash=placeholder_hash,
        name=payload.admin_name.strip(),
        role="admin",
        email_verified=False,
    )
    db.add(admin)
    db.flush()

    raw_token = issue_verification_token(db, admin.id)

    write_audit(
        db, org_id=org.id, user_id=actor_user_id, action="superadmin.org.created",
        resource_type="organization", resource_id=org.id,
        metadata={"admin_email": email, "plan_code": payload.plan_code},
    )
    db.commit()

    send_verification_email(email, raw_token)
    return CreateOrgResponse(org_id=org.id, admin_user_id=admin.id)


def update_organization(db: Session, org_id: str, payload: UpdateOrgRequest, actor_user_id: str) -> Organization:
    org = _require_org(db, org_id)
    if payload.name is not None:
        org.name = payload.name.strip()
    if payload.plan_code is not None:
        if payload.plan_code not in PLANS:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="unknown plan_code")
        org.plan_code = payload.plan_code
    write_audit(
        db, org_id=org.id, user_id=actor_user_id, action="superadmin.org.updated",
        resource_type="organization", resource_id=org.id,
        metadata={"name": org.name, "plan_code": org.plan_code},
    )
    db.commit()
    db.refresh(org)
    return org


def set_org_status(db: Session, org_id: str, new_status: str, actor_user_id: str) -> Organization:
    if new_status not in ("active", "suspended"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid status")
    org = _require_org(db, org_id)
    org.status = new_status
    action = "superadmin.org.suspended" if new_status == "suspended" else "superadmin.org.unsuspended"
    write_audit(
        db, org_id=org.id, user_id=actor_user_id, action=action,
        resource_type="organization", resource_id=org.id, metadata={},
    )
    db.commit()
    db.refresh(org)
    return org


def delete_organization(db: Session, org_id: str, actor_user_id: str) -> None:
    """Soft-delete: mark the org deleted (hidden from lists + login blocked).

    Reversible and avoids the RESTRICT-FK cascade across schedules/audit/
    subscriptions and the orphaning of vector-store namespaces. A hard purge can
    be added later as a dedicated background job if data removal is ever required.
    """
    org = _require_org(db, org_id)
    org.status = "deleted"
    write_audit(
        db, org_id=org.id, user_id=actor_user_id, action="superadmin.org.deleted",
        resource_type="organization", resource_id=org.id, metadata={"name": org.name},
    )
    db.commit()


def record_org_entry(db: Session, org_id: str, actor_user_id: str) -> None:
    """Audit a superadmin entering (impersonating) an org's dashboard."""
    _require_org(db, org_id)
    write_audit(
        db, org_id=org_id, user_id=actor_user_id, action="superadmin.org.entered",
        resource_type="organization", resource_id=org_id, metadata={},
    )
    db.commit()


_VALID_ROLES = {"viewer", "team_member", "admin"}


def _require_user_in_org(db: Session, org_id: str, user_id: str) -> User:
    user = db.query(User).filter(User.id == user_id, User.org_id == org_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    return user


def list_org_users(db: Session, org_id: str) -> list[User]:
    _require_org(db, org_id)
    return db.query(User).filter(User.org_id == org_id).order_by(User.email).all()


def create_org_user(db: Session, org_id: str, payload: CreateOrgUserRequest, actor_user_id: str) -> User:
    _require_org(db, org_id)
    if payload.role not in _VALID_ROLES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid role")
    email = payload.email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    placeholder_hash = hashlib.sha256(secrets.token_urlsafe(32).encode()).hexdigest()
    user = User(
        id=uuid_str(), org_id=org_id, email=email, password_hash=placeholder_hash,
        name=payload.name.strip(), role=payload.role, email_verified=False,
    )
    db.add(user)
    db.flush()

    raw_token = issue_verification_token(db, user.id)
    write_audit(
        db, org_id=org_id, user_id=actor_user_id, action="superadmin.user.created",
        resource_type="user", resource_id=user.id, metadata={"email": email, "role": payload.role},
    )
    db.commit()
    send_verification_email(email, raw_token)
    db.refresh(user)
    return user


def update_org_user(db: Session, org_id: str, user_id: str, payload: UpdateOrgUserRequest, actor_user_id: str) -> User:
    user = _require_user_in_org(db, org_id, user_id)
    if payload.role is not None:
        if payload.role not in _VALID_ROLES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid role")
        user.role = payload.role
    if payload.disabled is not None:
        user.disabled = payload.disabled
    write_audit(
        db, org_id=org_id, user_id=actor_user_id, action="superadmin.user.updated",
        resource_type="user", resource_id=user.id,
        metadata={"role": payload.role, "disabled": payload.disabled},
    )
    db.commit()
    db.refresh(user)
    return user


def delete_org_user(db: Session, org_id: str, user_id: str, actor_user_id: str) -> None:
    user = _require_user_in_org(db, org_id, user_id)
    write_audit(
        db, org_id=org_id, user_id=actor_user_id, action="superadmin.user.deleted",
        resource_type="user", resource_id=user.id, metadata={"email": user.email},
    )
    db.flush()
    db.delete(user)
    db.commit()


def reset_user_password(db: Session, org_id: str, user_id: str, actor_user_id: str) -> None:
    user = _require_user_in_org(db, org_id, user_id)
    # Invalidate the password and any outstanding verification tokens.
    user.password_hash = hashlib.sha256(secrets.token_urlsafe(32).encode()).hexdigest()
    db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == user.id,
        EmailVerificationToken.used == False,  # noqa: E712
    ).update({"used": True})
    # Issue a fresh set-password token via the shared helper.
    raw_token = issue_verification_token(db, user.id)
    write_audit(
        db, org_id=org_id, user_id=actor_user_id, action="superadmin.user.password_reset",
        resource_type="user", resource_id=user.id, metadata={},
    )
    db.commit()
    send_verification_email(user.email, raw_token)
