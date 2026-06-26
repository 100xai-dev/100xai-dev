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
    # FastAPI caches get_db per request, so routes that already depend on
    # get_db do not open a second session. The org lookup below only runs
    # for superadmins that supply an X-Acting-Org-Id header.
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
