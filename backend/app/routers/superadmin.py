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
