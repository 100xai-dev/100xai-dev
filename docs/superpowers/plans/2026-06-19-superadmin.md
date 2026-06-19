# Superadmin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a platform `superadmin` who can list/create/onboard/edit/suspend/delete every organization, manage any org's users, and "enter" any org to operate its full existing dashboard with read+write access.

**Architecture:** Acting-org context. The superadmin keeps their own session; entering an org sets a client cookie that adds an `X-Acting-Org-Id` header to every request. A backend dependency, *only after verifying from the JWT that the caller is a superadmin*, swaps the effective `org_id` to the target org — so every existing org-scoped route and dashboard page works unchanged. Cross-org management lives in a new guarded `/superadmin` API. A schema migration adds `organizations.status` (suspend) and `users.disabled`.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 + Alembic + PyJWT (backend, `backend/`); Next.js App Router + TypeScript (frontend, `frontend/`); pytest (backend tests).

**Spec:** `docs/superpowers/specs/2026-06-19-superadmin-design.md`

---

## File Structure

**Backend (create):**
- `backend/app/schemas/superadmin.py` — request/response models for `/superadmin`.
- `backend/app/services/superadmin.py` — cross-org CRUD, onboarding, suspend, user management (all write audit logs).
- `backend/app/routers/superadmin.py` — `/superadmin` routes, guarded by `require_superadmin`.
- `backend/app/scripts/__init__.py`, `backend/app/scripts/seed_superadmins.py` — idempotent superadmin provisioning.
- `backend/alembic/versions/20260619_0014_superadmin.py` — `organizations.status`, `users.disabled`.
- `backend/tests/test_acting_context.py`, `backend/tests/test_superadmin.py`, `backend/tests/test_superadmin_seed.py`.

**Backend (modify):**
- `backend/app/auth/rbac.py` — superadmin satisfies every role gate.
- `backend/app/deps.py` — `CurrentUser.is_superadmin`; acting-org resolution; `require_superadmin`.
- `backend/app/models/core.py` — `Organization.status`, `User.disabled`.
- `backend/app/routers/auth.py` — block suspended orgs / disabled users at login + refresh.
- `backend/app/config.py` — `superadmin_emails`, `superadmin_password`.
- `backend/app/main.py` — register the superadmin router.

**Frontend (create):**
- `frontend/app/superadmin/page.tsx` — orgs landing table.
- `frontend/app/superadmin/orgs/[id]/users/page.tsx` — per-org user management.
- `frontend/components/superadmin/create-org-form.tsx` — onboarding form.
- `frontend/components/superadmin/acting-banner.tsx` — "Acting as <Org>" bar.

**Frontend (modify):**
- `frontend/lib/types.ts` — superadmin DTOs.
- `frontend/lib/auth.ts` — acting-org cookie helpers.
- `frontend/lib/api.ts` — attach `X-Acting-Org-Id`; superadmin API functions.
- `frontend/context/AuthContext.tsx` — route superadmins to `/superadmin` on login.
- `frontend/app/layout.tsx` — mount the acting banner.

---

## Conventions for backend tests

`backend/tests/conftest.py` already provides fixtures/helpers used throughout:
- `client` — `TestClient` with `get_db` overridden to the test session.
- `db_session` — in-memory SQLite session (tables created from models).
- `create_user(session, email, role="admin", plan_code="free")` — creates an Organization + User, returns the user.
- `auth_headers(user)` — returns `{"Authorization": "Bearer <access token>"}`.

Run all backend tests from `backend/`: `pytest -q`.

---

## Task 1: superadmin satisfies every role gate

**Files:**
- Modify: `backend/app/auth/rbac.py`
- Test: `backend/tests/test_acting_context.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_acting_context.py`:

```python
import pytest

from app.auth.rbac import require_role
from fastapi import HTTPException


def test_require_role_allows_superadmin_for_any_set():
    # Should not raise even though "superadmin" is not in the allowed set.
    require_role("superadmin", {"admin"})
    require_role("superadmin", {"viewer"})


def test_require_role_still_blocks_unlisted_normal_role():
    with pytest.raises(HTTPException) as exc:
        require_role("viewer", {"admin"})
    assert exc.value.status_code == 403
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_acting_context.py -q`
Expected: FAIL — `test_require_role_allows_superadmin_for_any_set` raises HTTPException (superadmin not yet special-cased).

- [ ] **Step 3: Update `require_role`**

Replace the body of `backend/app/auth/rbac.py` with:

```python
from fastapi import HTTPException, status


ROLE_ORDER = {
    "viewer": 1,
    "team_member": 2,
    "admin": 3,
    "superadmin": 99,
}


def require_role(actual: str, allowed: set[str]) -> None:
    # A platform superadmin satisfies every role requirement.
    if actual == "superadmin":
        return
    if actual not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_acting_context.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/auth/rbac.py backend/tests/test_acting_context.py
git commit -m "feat(superadmin): superadmin role satisfies every role gate"
```

---

## Task 2: acting-org context + `require_superadmin` dependency

**Files:**
- Modify: `backend/app/deps.py`
- Test: `backend/tests/test_acting_context.py`

The new `CurrentUser.is_superadmin` flag is preserved through acting; when a superadmin sends `X-Acting-Org-Id` for an existing org, the effective context becomes that org with `role="admin"` (so both `require_role` and direct `role == "admin"` checks pass) while `is_superadmin` stays `True` (so `require_superadmin` still works and audit can attribute actions).

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_acting_context.py`:

```python
from tests.conftest import auth_headers, create_user


def test_superadmin_acting_header_scopes_to_target_org(client, db_session):
    target = create_user(db_session, "owner@acme.test", role="admin")
    superadmin = create_user(db_session, "root@platform.test", role="superadmin")

    headers = auth_headers(superadmin)
    headers["X-Acting-Org-Id"] = target.org_id

    # /v1/brands is org-scoped; acting as the target org must return 200
    # (empty list), not the superadmin's own org.
    res = client.get("/v1/brands", headers=headers)
    assert res.status_code == 200


def test_acting_header_ignored_for_non_superadmin(client, db_session):
    victim = create_user(db_session, "victim@acme.test", role="admin")
    attacker = create_user(db_session, "attacker@evil.test", role="admin")

    headers = auth_headers(attacker)
    headers["X-Acting-Org-Id"] = victim.org_id

    # The header must be ignored: attacker stays scoped to their own org.
    # Create a brand as the victim, then confirm the attacker cannot see it.
    from app.models import Brand
    brand = Brand(org_id=victim.org_id, name="Secret", dna_source="manual", status="DRAFT", created_by=victim.id)
    db_session.add(brand)
    db_session.commit()

    res = client.get("/v1/brands", headers=headers)
    assert res.status_code == 200
    names = [b["name"] for b in res.json()["items"]]
    assert "Secret" not in names


def test_superadmin_acting_on_unknown_org_returns_404(client, db_session):
    superadmin = create_user(db_session, "root2@platform.test", role="superadmin")
    headers = auth_headers(superadmin)
    headers["X-Acting-Org-Id"] = "00000000-0000-0000-0000-000000000000"
    res = client.get("/v1/brands", headers=headers)
    assert res.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_acting_context.py -q`
Expected: FAIL — acting header is not yet honored (`test_superadmin_acting...` returns the superadmin's own org / no 404).

- [ ] **Step 3: Implement acting-org resolution in `deps.py`**

Replace `backend/app/deps.py` with the following. Note: the previous `deps.py`
defined its **own** `get_db`, but the test suite (and most routers) use
`app.db.get_db`. Two routers (`brand_sources.py`, `integrations.py`) import
`get_db` from `app.deps`. To keep a single shared dependency object — so the
test override on `app.db.get_db` applies everywhere and `get_current_user` sees
the test session — re-export `app.db.get_db` here instead of redefining it.

```python
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.jwt import decode_access_token
from app.db import get_db  # re-exported: routers import get_db from app.deps too
from app.models import Organization

__all__ = ["CurrentUser", "get_db", "get_current_user", "require_superadmin"]


@dataclass(frozen=True)
class CurrentUser:
    id: str
    org_id: str
    role: str
    is_superadmin: bool = False


def get_current_user(
    authorization: str | None = Header(default=None),
    x_acting_org_id: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> CurrentUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token") from exc

    role = payload["role"]
    is_superadmin = role == "superadmin"

    # Acting-org override: honored ONLY for a verified superadmin. A normal user
    # who sets the header is ignored entirely (security boundary).
    if is_superadmin and x_acting_org_id:
        org = db.get(Organization, x_acting_org_id)
        if org is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="organization not found")
        return CurrentUser(id=payload["sub"], org_id=x_acting_org_id, role="admin", is_superadmin=True)

    return CurrentUser(id=payload["sub"], org_id=payload["org_id"], role=role, is_superadmin=is_superadmin)


def require_superadmin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not current_user.is_superadmin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="superadmin required")
    return current_user
```

Note: FastAPI maps the `x_acting_org_id` parameter to the `X-Acting-Org-Id` request header automatically.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_acting_context.py -q`
Expected: PASS (all tests, including Task 1's)

- [ ] **Step 5: Commit**

```bash
git add backend/app/deps.py backend/tests/test_acting_context.py
git commit -m "feat(superadmin): acting-org context + require_superadmin dependency"
```

---

## Task 3: schema migration — `organizations.status`, `users.disabled`

**Files:**
- Modify: `backend/app/models/core.py`
- Create: `backend/alembic/versions/20260619_0014_superadmin.py`

- [ ] **Step 1: Add columns to the models**

In `backend/app/models/core.py`, add `Boolean` is already imported. In the `Organization` class, after the `plan_code` line, add:

```python
    status: Mapped[str] = mapped_column(String, nullable=False, default="active", server_default="active")
```

In the `User` class, after the `email_verified_at` line, add:

```python
    disabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
```

- [ ] **Step 2: Write the migration**

Create `backend/alembic/versions/20260619_0014_superadmin.py`:

```python
"""superadmin: organization status + user disabled

Revision ID: 20260619_0014
Revises: 20260612_0013
Create Date: 2026-06-19
"""

from alembic import op
import sqlalchemy as sa

revision = "20260619_0014"
down_revision = "20260612_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
    )
    op.add_column(
        "users",
        sa.Column("disabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("users", "disabled")
    op.drop_column("organizations", "status")
```

- [ ] **Step 3: Verify the migration applies cleanly**

Run (from `backend/`, against a dev database): `alembic upgrade head`
Expected: applies revision `20260619_0014` with no error. Confirm head: `alembic current` shows `20260619_0014`.

If no dev DB is available, instead verify the revision chain is valid: `alembic history | head -3` should list `20260619_0014` above `20260612_0013`.

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/core.py backend/alembic/versions/20260619_0014_superadmin.py
git commit -m "feat(superadmin): add organizations.status and users.disabled"
```

---

## Task 4: block suspended orgs / disabled users at login + refresh

**Files:**
- Modify: `backend/app/routers/auth.py`
- Test: `backend/tests/test_superadmin.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_superadmin.py`:

```python
from app.auth.password import hash_password
from app.models import Organization, User
from app.models.base import uuid_str
from tests.conftest import auth_headers, create_user


def _make_login_user(db, email="login@acme.test", password="Test1234!"):
    org = Organization(id=uuid_str(), name="LoginOrg", plan_code="free")
    db.add(org)
    db.flush()
    user = User(
        id=uuid_str(), org_id=org.id, email=email, password_hash=hash_password(password),
        name="Login", role="admin", email_verified=True,
    )
    db.add(user)
    db.commit()
    return org, user


def test_login_blocked_when_org_suspended(client, db_session):
    org, user = _make_login_user(db_session, "susp@acme.test")
    org.status = "suspended"
    db_session.commit()
    res = client.post("/v1/auth/login", json={"email": "susp@acme.test", "password": "Test1234!"})
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "org_suspended"


def test_login_blocked_when_user_disabled(client, db_session):
    org, user = _make_login_user(db_session, "dis@acme.test")
    user.disabled = True
    db_session.commit()
    res = client.post("/v1/auth/login", json={"email": "dis@acme.test", "password": "Test1234!"})
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "account_disabled"


def test_login_blocked_when_org_deleted(client, db_session):
    org, user = _make_login_user(db_session, "del@acme.test")
    org.status = "deleted"
    db_session.commit()
    res = client.post("/v1/auth/login", json={"email": "del@acme.test", "password": "Test1234!"})
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "org_deleted"


def test_login_succeeds_when_active(client, db_session):
    _make_login_user(db_session, "ok@acme.test")
    res = client.post("/v1/auth/login", json={"email": "ok@acme.test", "password": "Test1234!"})
    assert res.status_code == 200
    assert "access_token" in res.json()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_superadmin.py -q`
Expected: FAIL — suspended/disabled logins currently return 200.

- [ ] **Step 3: Add the gates in `login`**

In `backend/app/routers/auth.py`, inside `login`, immediately after the `if not user.email_verified:` block (before fetching `org`), add:

```python
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "account_disabled", "email": user.email},
        )
```

Then, right after `org = db.get(Organization, user.org_id)` and its existing `if not org:` check, add:

```python
    if org.status != "active":
        # Covers both "suspended" and soft-"deleted" orgs.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": f"org_{org.status}"},
        )
```

- [ ] **Step 4: Add the same gates in `refresh`**

In `refresh`, after `user = db.get(User, claims["sub"])` and its `if not user:` check, add:

```python
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "account_disabled"},
        )
    org = db.get(Organization, user.org_id)
    if org is not None and org.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": f"org_{org.status}"},
        )
```

(Note: a superadmin acting on a suspended org is unaffected — the acting path in `deps.py` does not apply these gates.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_superadmin.py -q`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/auth.py backend/tests/test_superadmin.py
git commit -m "feat(superadmin): block suspended orgs and disabled users at login/refresh"
```

---

## Task 5: superadmin schemas

**Files:**
- Create: `backend/app/schemas/superadmin.py`

- [ ] **Step 1: Write the schemas**

Create `backend/app/schemas/superadmin.py`:

```python
from pydantic import BaseModel, EmailStr


class OrgListItem(BaseModel):
    id: str
    name: str
    plan_code: str
    status: str
    user_count: int
    brand_count: int


class OrgListResponse(BaseModel):
    items: list[OrgListItem]


class CreateOrgRequest(BaseModel):
    organization_name: str
    plan_code: str = "free"
    admin_name: str
    admin_email: EmailStr


class CreateOrgResponse(BaseModel):
    org_id: str
    admin_user_id: str


class UpdateOrgRequest(BaseModel):
    name: str | None = None
    plan_code: str | None = None


class OrgDetail(BaseModel):
    id: str
    name: str
    plan_code: str
    status: str


class OrgUserOut(BaseModel):
    id: str
    name: str | None
    email: str
    role: str
    email_verified: bool = False
    disabled: bool = False

    model_config = {"from_attributes": True}


class OrgUserListResponse(BaseModel):
    items: list[OrgUserOut]


class CreateOrgUserRequest(BaseModel):
    name: str
    email: EmailStr
    role: str = "team_member"


class UpdateOrgUserRequest(BaseModel):
    role: str | None = None
    disabled: bool | None = None


class MessageResponse(BaseModel):
    message: str
```

- [ ] **Step 2: Verify it imports**

Run: `python -c "import app.schemas.superadmin"`  (from `backend/`)
Expected: no output, exit 0.

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/superadmin.py
git commit -m "feat(superadmin): request/response schemas"
```

---

## Task 6: superadmin service — orgs (list, onboard, edit, suspend, delete) + audit

**Files:**
- Create: `backend/app/services/superadmin.py`
- Test: `backend/tests/test_superadmin.py`

This service reuses the existing audit helper (`app.services.audit.write_audit`) and the verification-token + email pattern from `app.routers.auth`.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_superadmin.py`:

```python
from app.models import AuditLog, Brand


def test_list_organizations_returns_counts(db_session):
    from app.services.superadmin import list_organizations
    u = create_user(db_session, "counts@acme.test", role="admin")
    db_session.add(Brand(org_id=u.org_id, name="B1", dna_source="manual", status="DRAFT", created_by=u.id))
    db_session.commit()

    items = list_organizations(db_session)
    row = next(i for i in items if i.id == u.org_id)
    assert row.user_count == 1
    assert row.brand_count == 1
    assert row.status == "active"


def test_create_organization_creates_org_admin_and_token(db_session, monkeypatch):
    import app.services.superadmin as svc
    sent = []
    monkeypatch.setattr(svc, "send_verification_email", lambda email, token: sent.append((email, token)))

    from app.schemas.superadmin import CreateOrgRequest
    from app.models import EmailVerificationToken, Organization, User

    actor = "superadmin-id"
    resp = svc.create_organization(
        db_session,
        CreateOrgRequest(organization_name="NewCo", plan_code="starter",
                         admin_name="Ann", admin_email="ann@newco.test"),
        actor_user_id=actor,
    )
    org = db_session.get(Organization, resp.org_id)
    assert org.name == "NewCo" and org.plan_code == "starter"
    admin = db_session.get(User, resp.admin_user_id)
    assert admin.role == "admin" and admin.email == "ann@newco.test" and admin.email_verified is False
    assert db_session.query(EmailVerificationToken).filter_by(user_id=admin.id).count() == 1
    assert len(sent) == 1
    assert db_session.query(AuditLog).filter_by(org_id=org.id, action="superadmin.org.created").count() == 1


def test_set_org_status_suspends_and_audits(db_session):
    from app.services.superadmin import set_org_status
    u = create_user(db_session, "tosuspend@acme.test", role="admin")
    set_org_status(db_session, u.org_id, "suspended", actor_user_id="root")
    from app.models import Organization
    assert db_session.get(Organization, u.org_id).status == "suspended"
    assert db_session.query(AuditLog).filter_by(org_id=u.org_id, action="superadmin.org.suspended").count() == 1


def test_delete_organization_soft_deletes_and_hides(db_session):
    from app.services.superadmin import delete_organization, list_organizations
    from app.models import Organization
    u = create_user(db_session, "todelete@acme.test", role="admin")
    org_id = u.org_id
    delete_organization(db_session, org_id, actor_user_id="root")
    org = db_session.get(Organization, org_id)
    assert org is not None and org.status == "deleted"
    # Soft-deleted orgs are hidden from the superadmin list.
    assert all(i.id != org_id for i in list_organizations(db_session))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_superadmin.py -q`
Expected: FAIL — `app.services.superadmin` does not exist yet.

- [ ] **Step 3: Implement the service**

Create `backend/app/services/superadmin.py`:

```python
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
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
    OrgListItem,
    UpdateOrgRequest,
)
from app.services.audit import write_audit
from app.services.billing_plans import PLANS
from app.services.email import send_verification_email


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

    # No usable password yet — the admin sets one via the verification/invite flow.
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

    settings = get_settings()
    raw_token = secrets.token_urlsafe(32)
    db.add(EmailVerificationToken(
        id=uuid_str(),
        user_id=admin.id,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.email_verification_expiry_hours),
    ))

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
        metadata={"name": payload.name, "plan_code": payload.plan_code},
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
```

- [ ] **Step 4: Confirm `write_audit` signature matches**

Open `backend/app/services/audit.py` and confirm `write_audit(db, *, org_id, user_id, action, resource_type=None, resource_id=None, brand_id=None, metadata=None)` accepts the keyword arguments used above (it is called the same way in `brand_service.py`). If the parameter is named `metadata_json` instead of `metadata`, adjust the calls accordingly.

Run: `pytest tests/test_superadmin.py -q`
Expected: PASS (org-service tests + the Task 4 login tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/superadmin.py backend/tests/test_superadmin.py
git commit -m "feat(superadmin): org service (list, onboard, edit, suspend, delete, audit)"
```

---

## Task 7: superadmin service — org user management

**Files:**
- Modify: `backend/app/services/superadmin.py`
- Test: `backend/tests/test_superadmin.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_superadmin.py`:

```python
def test_create_and_update_org_user(db_session):
    import app.services.superadmin as svc
    from app.schemas.superadmin import CreateOrgUserRequest, UpdateOrgUserRequest

    owner = create_user(db_session, "owner2@acme.test", role="admin")
    new_user = svc.create_org_user(
        db_session, owner.org_id,
        CreateOrgUserRequest(name="Bob", email="bob@acme.test", role="team_member"),
        actor_user_id="root",
    )
    assert new_user.role == "team_member" and new_user.org_id == owner.org_id

    updated = svc.update_org_user(
        db_session, owner.org_id, new_user.id,
        UpdateOrgUserRequest(disabled=True, role="viewer"), actor_user_id="root",
    )
    assert updated.disabled is True and updated.role == "viewer"


def test_update_user_rejects_cross_org(db_session):
    import app.services.superadmin as svc
    from app.schemas.superadmin import UpdateOrgUserRequest
    from fastapi import HTTPException
    import pytest

    org_a = create_user(db_session, "a@x.test", role="admin")
    org_b = create_user(db_session, "b@y.test", role="admin")
    with pytest.raises(HTTPException) as exc:
        svc.update_org_user(db_session, org_a.org_id, org_b.id, UpdateOrgUserRequest(role="viewer"), actor_user_id="root")
    assert exc.value.status_code == 404


def test_reset_password_issues_token(db_session, monkeypatch):
    import app.services.superadmin as svc
    sent = []
    monkeypatch.setattr(svc, "send_verification_email", lambda email, token: sent.append((email, token)))
    owner = create_user(db_session, "reset@acme.test", role="admin")
    svc.reset_user_password(db_session, owner.org_id, owner.id, actor_user_id="root")
    from app.models import EmailVerificationToken
    assert db_session.query(EmailVerificationToken).filter_by(user_id=owner.id).count() == 1
    assert len(sent) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_superadmin.py -q`
Expected: FAIL — `create_org_user` / `update_org_user` / `reset_user_password` don't exist.

- [ ] **Step 3: Implement the user-management functions**

Append to `backend/app/services/superadmin.py`:

```python
from app.schemas.superadmin import CreateOrgUserRequest, UpdateOrgUserRequest

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

    settings = get_settings()
    raw_token = secrets.token_urlsafe(32)
    db.add(EmailVerificationToken(
        id=uuid_str(), user_id=user.id,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.email_verification_expiry_hours),
    ))
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
    # Invalidate the password and issue a fresh verification/set-password token.
    user.password_hash = hashlib.sha256(secrets.token_urlsafe(32).encode()).hexdigest()
    db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == user.id,
        EmailVerificationToken.used == False,  # noqa: E712
    ).update({"used": True})
    settings = get_settings()
    raw_token = secrets.token_urlsafe(32)
    db.add(EmailVerificationToken(
        id=uuid_str(), user_id=user.id,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.email_verification_expiry_hours),
    ))
    write_audit(
        db, org_id=org_id, user_id=actor_user_id, action="superadmin.user.password_reset",
        resource_type="user", resource_id=user.id, metadata={},
    )
    db.commit()
    send_verification_email(user.email, raw_token)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_superadmin.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/superadmin.py backend/tests/test_superadmin.py
git commit -m "feat(superadmin): org user management service"
```

---

## Task 8: superadmin router + register in app

**Files:**
- Create: `backend/app/routers/superadmin.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_superadmin.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_superadmin.py`:

```python
def test_routes_require_superadmin(client, db_session):
    normal = create_user(db_session, "normal@acme.test", role="admin")
    res = client.get("/v1/superadmin/orgs", headers=auth_headers(normal))
    assert res.status_code == 403


def test_superadmin_lists_and_creates_orgs(client, db_session, monkeypatch):
    import app.services.superadmin as svc
    monkeypatch.setattr(svc, "send_verification_email", lambda email, token: None)

    root = create_user(db_session, "root3@platform.test", role="superadmin")
    headers = auth_headers(root)

    res = client.get("/v1/superadmin/orgs", headers=headers)
    assert res.status_code == 200
    assert any(o["id"] == root.org_id for o in res.json()["items"])

    res = client.post("/v1/superadmin/orgs", headers=headers, json={
        "organization_name": "ApiCo", "plan_code": "free",
        "admin_name": "Cara", "admin_email": "cara@apico.test",
    })
    assert res.status_code == 201
    body = res.json()
    assert body["org_id"] and body["admin_user_id"]


def test_superadmin_enter_org_audits(client, db_session):
    root = create_user(db_session, "root4@platform.test", role="superadmin")
    target = create_user(db_session, "t@acme.test", role="admin")
    res = client.post(f"/v1/superadmin/orgs/{target.org_id}/enter", headers=auth_headers(root))
    assert res.status_code == 200
    from app.models import AuditLog
    assert db_session.query(AuditLog).filter_by(org_id=target.org_id, action="superadmin.org.entered").count() == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_superadmin.py -q`
Expected: FAIL — `/v1/superadmin/*` returns 404 (router not registered).

- [ ] **Step 3: Write the router**

Create `backend/app/routers/superadmin.py`:

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import CurrentUser, require_superadmin
from app.schemas.superadmin import (
    CreateOrgRequest,
    CreateOrgResponse,
    CreateOrgUserRequest,
    MessageResponse,
    OrgDetail,
    OrgListResponse,
    OrgUserListResponse,
    OrgUserOut,
    UpdateOrgRequest,
    UpdateOrgUserRequest,
)
from app.services import superadmin as svc

router = APIRouter(prefix="/superadmin", tags=["superadmin"], dependencies=[Depends(require_superadmin)])


@router.get("/orgs", response_model=OrgListResponse)
def list_orgs(db: Session = Depends(get_db)) -> OrgListResponse:
    return OrgListResponse(items=svc.list_organizations(db))


@router.post("/orgs", response_model=CreateOrgResponse, status_code=status.HTTP_201_CREATED)
def create_org(
    payload: CreateOrgRequest,
    db: Session = Depends(get_db),
    actor: CurrentUser = Depends(require_superadmin),
) -> CreateOrgResponse:
    return svc.create_organization(db, payload, actor_user_id=actor.id)


@router.patch("/orgs/{org_id}", response_model=OrgDetail)
def update_org(
    org_id: str,
    payload: UpdateOrgRequest,
    db: Session = Depends(get_db),
    actor: CurrentUser = Depends(require_superadmin),
) -> OrgDetail:
    org = svc.update_organization(db, org_id, payload, actor_user_id=actor.id)
    return OrgDetail(id=org.id, name=org.name, plan_code=org.plan_code, status=org.status)


@router.post("/orgs/{org_id}/suspend", response_model=OrgDetail)
def suspend_org(org_id: str, db: Session = Depends(get_db), actor: CurrentUser = Depends(require_superadmin)) -> OrgDetail:
    org = svc.set_org_status(db, org_id, "suspended", actor_user_id=actor.id)
    return OrgDetail(id=org.id, name=org.name, plan_code=org.plan_code, status=org.status)


@router.post("/orgs/{org_id}/unsuspend", response_model=OrgDetail)
def unsuspend_org(org_id: str, db: Session = Depends(get_db), actor: CurrentUser = Depends(require_superadmin)) -> OrgDetail:
    org = svc.set_org_status(db, org_id, "active", actor_user_id=actor.id)
    return OrgDetail(id=org.id, name=org.name, plan_code=org.plan_code, status=org.status)


@router.delete("/orgs/{org_id}", response_model=MessageResponse)
def delete_org(org_id: str, db: Session = Depends(get_db), actor: CurrentUser = Depends(require_superadmin)) -> MessageResponse:
    svc.delete_organization(db, org_id, actor_user_id=actor.id)
    return MessageResponse(message="organization deleted")


@router.post("/orgs/{org_id}/enter", response_model=MessageResponse)
def enter_org(org_id: str, db: Session = Depends(get_db), actor: CurrentUser = Depends(require_superadmin)) -> MessageResponse:
    svc.record_org_entry(db, org_id, actor_user_id=actor.id)
    return MessageResponse(message="entered")


@router.get("/orgs/{org_id}/users", response_model=OrgUserListResponse)
def list_users(org_id: str, db: Session = Depends(get_db)) -> OrgUserListResponse:
    users = svc.list_org_users(db, org_id)
    return OrgUserListResponse(items=[OrgUserOut.model_validate(u) for u in users])


@router.post("/orgs/{org_id}/users", response_model=OrgUserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    org_id: str,
    payload: CreateOrgUserRequest,
    db: Session = Depends(get_db),
    actor: CurrentUser = Depends(require_superadmin),
) -> OrgUserOut:
    return OrgUserOut.model_validate(svc.create_org_user(db, org_id, payload, actor_user_id=actor.id))


@router.patch("/orgs/{org_id}/users/{user_id}", response_model=OrgUserOut)
def update_user(
    org_id: str,
    user_id: str,
    payload: UpdateOrgUserRequest,
    db: Session = Depends(get_db),
    actor: CurrentUser = Depends(require_superadmin),
) -> OrgUserOut:
    return OrgUserOut.model_validate(svc.update_org_user(db, org_id, user_id, payload, actor_user_id=actor.id))


@router.delete("/orgs/{org_id}/users/{user_id}", response_model=MessageResponse)
def delete_user(
    org_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    actor: CurrentUser = Depends(require_superadmin),
) -> MessageResponse:
    svc.delete_org_user(db, org_id, user_id, actor_user_id=actor.id)
    return MessageResponse(message="user deleted")


@router.post("/orgs/{org_id}/users/{user_id}/reset-password", response_model=MessageResponse)
def reset_password(
    org_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    actor: CurrentUser = Depends(require_superadmin),
) -> MessageResponse:
    svc.reset_user_password(db, org_id, user_id, actor_user_id=actor.id)
    return MessageResponse(message="password reset email sent")
```

- [ ] **Step 4: Register the router in `main.py`**

In `backend/app/main.py`, add the import alongside the others:

```python
from app.routers.superadmin import router as superadmin_router
```

and add the include alongside the others:

```python
app.include_router(superadmin_router, prefix="/v1")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_superadmin.py tests/test_acting_context.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/superadmin.py backend/app/main.py backend/tests/test_superadmin.py
git commit -m "feat(superadmin): /superadmin router for cross-org management"
```

---

## Task 9: superadmin seeding (config + idempotent script)

**Files:**
- Modify: `backend/app/config.py`
- Create: `backend/app/scripts/__init__.py`, `backend/app/scripts/seed_superadmins.py`
- Test: `backend/tests/test_superadmin_seed.py`

- [ ] **Step 1: Add config settings**

In `backend/app/config.py`, add inside the `Settings` class (e.g. after the Terms section):

```python
    # --- Superadmin provisioning ---
    superadmin_emails: str = ""  # comma-separated list of platform superadmin emails
    superadmin_password: str | None = None  # optional shared bootstrap password
```

- [ ] **Step 2: Write the failing test**

Create `backend/tests/test_superadmin_seed.py`:

```python
from app.models import Organization, User


def test_seed_creates_and_is_idempotent(db_session, monkeypatch):
    import app.scripts.seed_superadmins as seed

    class FakeSettings:
        superadmin_emails = "root@platform.test, ops@platform.test"
        superadmin_password = "Bootstrap123!"

    monkeypatch.setattr(seed, "get_settings", lambda: FakeSettings())

    seed.seed_superadmins(db_session)
    users = db_session.query(User).filter(User.role == "superadmin").all()
    assert {u.email for u in users} == {"root@platform.test", "ops@platform.test"}
    assert all(u.email_verified for u in users)
    system_orgs = db_session.query(Organization).filter(Organization.name == seed.SYSTEM_ORG_NAME).count()
    assert system_orgs == 1

    # Re-run: no duplicates.
    seed.seed_superadmins(db_session)
    assert db_session.query(User).filter(User.role == "superadmin").count() == 2
    assert db_session.query(Organization).filter(Organization.name == seed.SYSTEM_ORG_NAME).count() == 1


def test_seed_promotes_existing_user(db_session, monkeypatch):
    import app.scripts.seed_superadmins as seed
    from tests.conftest import create_user

    existing = create_user(db_session, "promote@platform.test", role="admin")

    class FakeSettings:
        superadmin_emails = "promote@platform.test"
        superadmin_password = "Bootstrap123!"

    monkeypatch.setattr(seed, "get_settings", lambda: FakeSettings())
    seed.seed_superadmins(db_session)
    db_session.refresh(existing)
    assert existing.role == "superadmin" and existing.email_verified is True
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_superadmin_seed.py -q`
Expected: FAIL — `app.scripts.seed_superadmins` does not exist.

- [ ] **Step 4: Implement the seed script**

Create `backend/app/scripts/__init__.py` (empty file).

Create `backend/app/scripts/seed_superadmins.py`:

```python
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_superadmin_seed.py -q`
Expected: PASS (2 passed)

- [ ] **Step 6: Run the whole backend suite (no regressions)**

Run: `pytest -q`
Expected: PASS (existing suite + new tests). Investigate and fix any failure before committing.

- [ ] **Step 7: Commit**

```bash
git add backend/app/config.py backend/app/scripts/ backend/tests/test_superadmin_seed.py
git commit -m "feat(superadmin): idempotent seed script + config"
```

---

## Task 10: frontend — types + acting-org cookie helpers + API client

**Files:**
- Modify: `frontend/lib/types.ts`, `frontend/lib/auth.ts`, `frontend/lib/api.ts`

- [ ] **Step 1: Add DTO types**

Append to `frontend/lib/types.ts`:

```typescript
// ─────────────────────────────────────────────────────────────────────────────
// Superadmin — backend/app/schemas/superadmin.py
// ─────────────────────────────────────────────────────────────────────────────
export interface OrgListItem {
  id: string;
  name: string;
  plan_code: string;
  status: string;
  user_count: number;
  brand_count: number;
}

export interface OrgListResponse {
  items: OrgListItem[];
}

export interface CreateOrgRequest {
  organization_name: string;
  plan_code: string;
  admin_name: string;
  admin_email: string;
}

export interface CreateOrgResponse {
  org_id: string;
  admin_user_id: string;
}

export interface UpdateOrgRequest {
  name?: string;
  plan_code?: string;
}

export interface OrgUserOut {
  id: string;
  name: string | null;
  email: string;
  role: string;
  email_verified: boolean;
  disabled: boolean;
}

export interface OrgUserListResponse {
  items: OrgUserOut[];
}

export interface CreateOrgUserRequest {
  name: string;
  email: string;
  role: string;
}

export interface UpdateOrgUserRequest {
  role?: string;
  disabled?: boolean;
}
```

- [ ] **Step 2: Add acting-org cookie helpers**

In `frontend/lib/auth.ts`, add these constants and functions (the cookie — not localStorage — is what the proxy forwards as a header source; the name is stored for the banner):

```typescript
const ACTING_ORG_KEY = "100xai_acting_org";
const ACTING_ORG_NAME_KEY = "100xai_acting_org_name";

export function setActingOrg(orgId: string, orgName: string): void {
  document.cookie = `${ACTING_ORG_KEY}=${orgId}; path=/; max-age=86400; SameSite=Lax`;
  localStorage.setItem(ACTING_ORG_NAME_KEY, orgName);
}

export function clearActingOrg(): void {
  document.cookie = `${ACTING_ORG_KEY}=; path=/; max-age=0`;
  localStorage.removeItem(ACTING_ORG_NAME_KEY);
}

export function getActingOrgId(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)100xai_acting_org=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export function getActingOrgName(): string | null {
  return typeof window === "undefined" ? null : localStorage.getItem(ACTING_ORG_NAME_KEY);
}
```

Also extend `clearSession()` so logout clears the acting cookie — add this line inside `clearSession()`:

```typescript
  document.cookie = `100xai_acting_org=; path=/; max-age=0`;
```

- [ ] **Step 3: Attach the acting-org header in `apiRequest`**

In `frontend/lib/api.ts`, inside `apiRequest`, after the `if (isServer()) { ... }` block that sets `Authorization`, add header propagation for both client and server contexts. Replace the existing server-only block with:

```typescript
  if (isServer()) {
    const { cookies } = await import("next/headers");
    const cookieStore = await cookies();
    const token = cookieStore.get("100xai_access_token")?.value;
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    const actingOrg = cookieStore.get("100xai_acting_org")?.value;
    if (actingOrg) {
      headers["X-Acting-Org-Id"] = actingOrg;
    }
  } else {
    const match = document.cookie.match(/(?:^|;\s*)100xai_acting_org=([^;]+)/);
    if (match) {
      headers["X-Acting-Org-Id"] = decodeURIComponent(match[1]);
    }
  }
```

- [ ] **Step 4: Add superadmin API functions**

Append to `frontend/lib/api.ts` (add the new type imports to the existing import block at the top: `OrgListResponse, CreateOrgRequest, CreateOrgResponse, UpdateOrgRequest, OrgUserListResponse, OrgUserOut, CreateOrgUserRequest, UpdateOrgUserRequest`):

```typescript
// ─────────────────────────────────────────────────────────────────────────────
// Superadmin — /v1/superadmin
// ─────────────────────────────────────────────────────────────────────────────
export function listOrganizations(): Promise<OrgListResponse> {
  return apiRequest<OrgListResponse>("/v1/superadmin/orgs");
}

export function createOrganization(payload: CreateOrgRequest): Promise<CreateOrgResponse> {
  return apiRequest<CreateOrgResponse>("/v1/superadmin/orgs", { method: "POST", body: payload });
}

export function updateOrganization(orgId: string, payload: UpdateOrgRequest): Promise<unknown> {
  return apiRequest(`/v1/superadmin/orgs/${orgId}`, { method: "PATCH", body: payload });
}

export function suspendOrganization(orgId: string): Promise<unknown> {
  return apiRequest(`/v1/superadmin/orgs/${orgId}/suspend`, { method: "POST" });
}

export function unsuspendOrganization(orgId: string): Promise<unknown> {
  return apiRequest(`/v1/superadmin/orgs/${orgId}/unsuspend`, { method: "POST" });
}

export function deleteOrganization(orgId: string): Promise<unknown> {
  return apiRequest(`/v1/superadmin/orgs/${orgId}`, { method: "DELETE" });
}

export function enterOrganization(orgId: string): Promise<unknown> {
  return apiRequest(`/v1/superadmin/orgs/${orgId}/enter`, { method: "POST" });
}

export function listOrgUsers(orgId: string): Promise<OrgUserListResponse> {
  return apiRequest<OrgUserListResponse>(`/v1/superadmin/orgs/${orgId}/users`);
}

export function createOrgUser(orgId: string, payload: CreateOrgUserRequest): Promise<OrgUserOut> {
  return apiRequest<OrgUserOut>(`/v1/superadmin/orgs/${orgId}/users`, { method: "POST", body: payload });
}

export function updateOrgUser(orgId: string, userId: string, payload: UpdateOrgUserRequest): Promise<OrgUserOut> {
  return apiRequest<OrgUserOut>(`/v1/superadmin/orgs/${orgId}/users/${userId}`, { method: "PATCH", body: payload });
}

export function deleteOrgUser(orgId: string, userId: string): Promise<unknown> {
  return apiRequest(`/v1/superadmin/orgs/${orgId}/users/${userId}`, { method: "DELETE" });
}

export function resetOrgUserPassword(orgId: string, userId: string): Promise<unknown> {
  return apiRequest(`/v1/superadmin/orgs/${orgId}/users/${userId}/reset-password`, { method: "POST" });
}
```

- [ ] **Step 5: Type-check**

Run (from `frontend/`): `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/types.ts frontend/lib/auth.ts frontend/lib/api.ts
git commit -m "feat(superadmin): frontend types, acting-org cookie, API client"
```

---

## Task 11: frontend — route superadmins to /superadmin on login

**Files:**
- Modify: `frontend/context/AuthContext.tsx`

- [ ] **Step 1: Redirect after login based on role**

In `frontend/context/AuthContext.tsx`, in the `login` callback, replace the post-login redirect:

```typescript
    applySession(await res.json() as AuthResponse);
    router.push("/brands");
```

with:

```typescript
    const data = await res.json() as AuthResponse;
    applySession(data);
    router.push(data.user.role === "superadmin" ? "/superadmin" : "/brands");
```

- [ ] **Step 2: Manual verification (no frontend unit-test harness in repo)**

Run the app (`npm run dev` in `frontend/`, backend running). Seed a superadmin (Task 9), log in as them, and confirm the browser lands on `/superadmin`. A normal user still lands on `/brands`.

- [ ] **Step 3: Commit**

```bash
git add frontend/context/AuthContext.tsx
git commit -m "feat(superadmin): route superadmins to /superadmin on login"
```

---

## Task 12: frontend — "Acting as" banner

**Files:**
- Create: `frontend/components/superadmin/acting-banner.tsx`
- Modify: `frontend/app/layout.tsx`

- [ ] **Step 1: Build the banner**

Create `frontend/components/superadmin/acting-banner.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { clearActingOrg, getActingOrgId, getActingOrgName } from "@/lib/auth";

export function ActingBanner() {
  const router = useRouter();
  const [name, setName] = useState<string | null>(null);

  useEffect(() => {
    if (getActingOrgId()) {
      setName(getActingOrgName() ?? "organization");
    }
  }, []);

  if (!name) return null;

  const exit = () => {
    clearActingOrg();
    setName(null);
    router.push("/superadmin");
    router.refresh();
  };

  return (
    <div
      style={{
        background: "#b91c1c",
        color: "white",
        padding: "8px 16px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        fontSize: 14,
        position: "sticky",
        top: 0,
        zIndex: 50,
      }}
    >
      <span>
        Superadmin — acting as <b>{name}</b>
      </span>
      <button
        onClick={exit}
        style={{ background: "white", color: "#b91c1c", border: "none", borderRadius: 4, padding: "4px 12px", cursor: "pointer", fontWeight: 600 }}
      >
        Exit org
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Mount the banner in the root layout**

In `frontend/app/layout.tsx`, import and render `<ActingBanner />` at the very top of the body (inside whatever provider wraps the app, above the page content):

```tsx
import { ActingBanner } from "@/components/superadmin/acting-banner";
```

and place `<ActingBanner />` immediately inside the top-level container that wraps `{children}` (before `{children}`).

- [ ] **Step 3: Type-check**

Run (from `frontend/`): `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/superadmin/acting-banner.tsx frontend/app/layout.tsx
git commit -m "feat(superadmin): acting-as banner with exit"
```

---

## Task 13: frontend — superadmin orgs landing + create-org form

**Files:**
- Create: `frontend/components/superadmin/create-org-form.tsx`, `frontend/app/superadmin/page.tsx`

- [ ] **Step 1: Build the create-org form**

Create `frontend/components/superadmin/create-org-form.tsx`:

```tsx
"use client";

import { useState } from "react";

import { createOrganization } from "@/lib/api";

export function CreateOrgForm({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [orgName, setOrgName] = useState("");
  const [plan, setPlan] = useState("free");
  const [adminName, setAdminName] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!open) {
    return <button onClick={() => setOpen(true)}>+ Create organization</button>;
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await createOrganization({
        organization_name: orgName,
        plan_code: plan,
        admin_name: adminName,
        admin_email: adminEmail,
      });
      setOpen(false);
      setOrgName(""); setAdminName(""); setAdminEmail(""); setPlan("free");
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create organization");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} style={{ display: "grid", gap: 8, maxWidth: 360, padding: 16, border: "1px solid #ddd", borderRadius: 8 }}>
      <h3>Create organization</h3>
      <input placeholder="Organization name" value={orgName} onChange={(e) => setOrgName(e.target.value)} required />
      <select value={plan} onChange={(e) => setPlan(e.target.value)}>
        <option value="free">free</option>
        <option value="starter">starter</option>
        <option value="pro">pro</option>
      </select>
      <input placeholder="Admin name" value={adminName} onChange={(e) => setAdminName(e.target.value)} required />
      <input type="email" placeholder="Admin email" value={adminEmail} onChange={(e) => setAdminEmail(e.target.value)} required />
      {error && <p style={{ color: "red" }}>{error}</p>}
      <div style={{ display: "flex", gap: 8 }}>
        <button type="submit" disabled={busy}>{busy ? "Creating…" : "Create"}</button>
        <button type="button" onClick={() => setOpen(false)}>Cancel</button>
      </div>
    </form>
  );
}
```

- [ ] **Step 2: Build the orgs landing page**

Create `frontend/app/superadmin/page.tsx`:

```tsx
"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { CreateOrgForm } from "@/components/superadmin/create-org-form";
import {
  deleteOrganization,
  enterOrganization,
  listOrganizations,
  suspendOrganization,
  unsuspendOrganization,
} from "@/lib/api";
import { setActingOrg } from "@/lib/auth";
import type { OrgListItem } from "@/lib/types";

export default function SuperadminPage() {
  const router = useRouter();
  const [orgs, setOrgs] = useState<OrgListItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await listOrganizations();
      setOrgs(res.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load organizations");
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const enter = async (org: OrgListItem) => {
    await enterOrganization(org.id);
    setActingOrg(org.id, org.name);
    router.push("/brands");
    router.refresh();
  };

  const toggleSuspend = async (org: OrgListItem) => {
    if (org.status === "suspended") await unsuspendOrganization(org.id);
    else await suspendOrganization(org.id);
    void load();
  };

  const remove = async (org: OrgListItem) => {
    const typed = window.prompt(`Type the org name to permanently delete it:\n${org.name}`);
    if (typed !== org.name) return;
    await deleteOrganization(org.id);
    void load();
  };

  return (
    <main style={{ padding: 24 }}>
      <h1>Organizations</h1>
      {error && <p style={{ color: "red" }}>{error}</p>}
      <div style={{ margin: "16px 0" }}>
        <CreateOrgForm onCreated={load} />
      </div>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "2px solid #ddd" }}>
            <th>Name</th><th>Plan</th><th>Status</th><th>Users</th><th>Brands</th><th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {orgs.map((o) => (
            <tr key={o.id} style={{ borderBottom: "1px solid #eee" }}>
              <td>{o.name}</td>
              <td>{o.plan_code}</td>
              <td>{o.status}</td>
              <td>{o.user_count}</td>
              <td>{o.brand_count}</td>
              <td style={{ display: "flex", gap: 8 }}>
                <button onClick={() => enter(o)}>Enter</button>
                <button onClick={() => router.push(`/superadmin/orgs/${o.id}/users`)}>Users</button>
                <button onClick={() => toggleSuspend(o)}>{o.status === "suspended" ? "Unsuspend" : "Suspend"}</button>
                <button onClick={() => remove(o)} style={{ color: "#b91c1c" }}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
```

- [ ] **Step 3: Type-check**

Run (from `frontend/`): `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Manual verification**

As a seeded superadmin: the page lists all orgs with counts; "Create organization" adds one; "Enter" sets the banner and lands on `/brands` showing that org's brands; Suspend/Unsuspend toggles status; Delete requires typing the exact name.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/superadmin/create-org-form.tsx frontend/app/superadmin/page.tsx
git commit -m "feat(superadmin): orgs landing page + onboarding form"
```

---

## Task 14: frontend — per-org user management page

**Files:**
- Create: `frontend/app/superadmin/orgs/[id]/users/page.tsx`

- [ ] **Step 1: Build the user-management page**

Create `frontend/app/superadmin/orgs/[id]/users/page.tsx`:

```tsx
"use client";

import { use, useCallback, useEffect, useState } from "react";

import {
  createOrgUser,
  deleteOrgUser,
  listOrgUsers,
  resetOrgUserPassword,
  updateOrgUser,
} from "@/lib/api";
import type { OrgUserOut } from "@/lib/types";

const ROLES = ["viewer", "team_member", "admin"];

export default function OrgUsersPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: orgId } = use(params);
  const [users, setUsers] = useState<OrgUserOut[]>([]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("team_member");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await listOrgUsers(orgId);
      setUsers(res.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load users");
    }
  }, [orgId]);

  useEffect(() => { void load(); }, [load]);

  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await createOrgUser(orgId, { name, email, role });
      setName(""); setEmail(""); setRole("team_member");
      void load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add user");
    }
  };

  return (
    <main style={{ padding: 24 }}>
      <h1>Users</h1>
      {error && <p style={{ color: "red" }}>{error}</p>}

      <form onSubmit={add} style={{ display: "flex", gap: 8, margin: "16px 0", flexWrap: "wrap" }}>
        <input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} required />
        <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <select value={role} onChange={(e) => setRole(e.target.value)}>
          {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        <button type="submit">Add user</button>
      </form>

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "2px solid #ddd" }}>
            <th>Email</th><th>Name</th><th>Role</th><th>Status</th><th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id} style={{ borderBottom: "1px solid #eee" }}>
              <td>{u.email}</td>
              <td>{u.name}</td>
              <td>
                <select
                  value={u.role}
                  onChange={async (e) => { await updateOrgUser(orgId, u.id, { role: e.target.value }); void load(); }}
                >
                  {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
              </td>
              <td>{u.disabled ? "disabled" : "active"}</td>
              <td style={{ display: "flex", gap: 8 }}>
                <button onClick={async () => { await updateOrgUser(orgId, u.id, { disabled: !u.disabled }); void load(); }}>
                  {u.disabled ? "Enable" : "Disable"}
                </button>
                <button onClick={async () => { await resetOrgUserPassword(orgId, u.id); }}>Reset pwd</button>
                <button
                  style={{ color: "#b91c1c" }}
                  onClick={async () => {
                    if (window.confirm(`Delete ${u.email}?`)) { await deleteOrgUser(orgId, u.id); void load(); }
                  }}
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
```

- [ ] **Step 2: Type-check**

Run (from `frontend/`): `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Manual verification**

From the orgs landing, click "Users" on an org: list shows that org's users; add creates a user (invite email logged to backend console in dev); role dropdown updates; Disable/Enable toggles; Reset pwd succeeds; Delete removes after confirm.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/superadmin/orgs/
git commit -m "feat(superadmin): per-org user management page"
```

---

## Task 15: end-to-end verification

**Files:** none (verification only)

- [ ] **Step 1: Backend suite green**

Run (from `backend/`): `pytest -q`
Expected: all tests pass.

- [ ] **Step 2: Frontend builds**

Run (from `frontend/`): `npx tsc --noEmit && npm run build`
Expected: type-check and production build succeed.

- [ ] **Step 3: Manual happy-path**

With backend + frontend running and a superadmin seeded:
1. Log in as superadmin → lands on `/superadmin`, lists all orgs.
2. Create a new org with an admin email → row appears; check backend console for the verification email link.
3. Enter the new org → red banner shows "acting as <Org>", `/brands` shows that org's (empty) dashboard; create a brand → succeeds (write access through acting context).
4. Exit org via the banner → returns to `/superadmin`, banner gone.
5. Manage users on an org → add/disable/role-change/reset/delete all work.
6. Suspend an org → log in (incognito) as that org's user → blocked with `org_suspended`. Unsuspend → login works.
7. As a normal admin user, confirm `/superadmin/orgs` returns 403 and that manually setting an `X-Acting-Org-Id` cookie does not grant access to another org.

- [ ] **Step 4: Commit any fixes, then finish**

```bash
git add -A
git commit -m "test(superadmin): end-to-end verification fixes"
```

When complete, consider the `superpowers:finishing-a-development-branch` skill to open a PR.

---

## Self-Review notes (addressed)

- **Spec coverage:** identity/provisioning (Tasks 1, 9), acting-org mechanism (Task 2), superadmin API incl. onboard/edit/suspend/delete/users (Tasks 5–8), suspend schema + login gate (Tasks 3–4), audit incl. enter-org (Tasks 6–8), frontend login routing/banner/landing/users/header plumbing (Tasks 10–14), testing (per-task + Task 15). All spec sections map to tasks.
- **Type consistency:** `CurrentUser.is_superadmin`, `require_superadmin`, service function names (`list_organizations`, `create_organization`, `update_organization`, `set_org_status`, `delete_organization`, `record_org_entry`, `list_org_users`, `create_org_user`, `update_org_user`, `delete_org_user`, `reset_user_password`) are used identically across service, router, and tests. Frontend API names match between `lib/api.ts` and the pages.
- **Known integration point to verify during Task 6:** `write_audit`'s metadata kwarg name (`metadata` vs `metadata_json`) — Step 4 of Task 6 calls this out explicitly.
