import re
from pydantic import BaseModel, EmailStr, field_validator


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    organization_name: str
    accept_terms: bool = False

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

    @field_validator("accept_terms")
    @classmethod
    def must_accept_terms(cls, v: bool) -> bool:
        if not v:
            raise ValueError("You must accept the Terms & Conditions to sign up")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class UserOut(BaseModel):
    id: str
    name: str | None
    email: str
    role: str
    org_id: str
    email_verified: bool = False

    model_config = {"from_attributes": True}


class OrgOut(BaseModel):
    id: str
    name: str
    plan_code: str = "free"

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    user: UserOut
    organization: OrgOut
    access_token: str
    refresh_token: str
    terms_acceptance_required: bool = False
    terms_current_version: str | None = None


class SignupResponse(BaseModel):
    user: UserOut
    organization: OrgOut
    requires_verification: bool = True


class MessageResponse(BaseModel):
    message: str


class AccessTokenResponse(BaseModel):
    access_token: str


class MeResponse(BaseModel):
    user: UserOut
    organization: OrgOut
    terms_acceptance_required: bool = False
    terms_current_version: str | None = None
