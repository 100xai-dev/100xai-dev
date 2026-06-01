import re
from pydantic import BaseModel, EmailStr, field_validator


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    organization_name: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @field_validator("organization_name")
    @classmethod
    def org_name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Organization name cannot be empty")
        return v.strip()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: str
    name: str | None
    email: str
    role: str
    org_id: str

    model_config = {"from_attributes": True}


class OrgOut(BaseModel):
    id: str
    name: str

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    user: UserOut
    organization: OrgOut
    access_token: str
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str


class MeResponse(BaseModel):
    user: UserOut
    organization: OrgOut
