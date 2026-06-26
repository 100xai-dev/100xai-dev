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
