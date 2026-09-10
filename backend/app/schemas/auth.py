from typing import Any

from pydantic import BaseModel, EmailStr, Field

from app.schemas.organization import OrganizationSummary
from app.schemas.user import UserRead


class RegisterRequest(BaseModel):
    organization_name: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    mobile: str | None = Field(None, max_length=30)
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AppSignupRequest(BaseModel):
    """Public signup from a builder page — field keys map to user + profile."""

    software_id: str = Field(..., min_length=1)
    page_id: str | None = None
    values: dict[str, Any] = Field(default_factory=dict)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AppSignupResponse(BaseModel):
    user: UserRead
    tokens: TokenResponse
    profile: dict[str, Any] = Field(default_factory=dict)


class LogoutRequest(BaseModel):
    refresh_token: str


class RegisterResponse(BaseModel):
    user: UserRead
    organization: OrganizationSummary
    tokens: TokenResponse
