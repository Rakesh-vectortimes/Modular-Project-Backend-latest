from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.enums import UserRole, UserStatus
from app.schemas.organization import OrganizationSummary


class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    mobile: str | None = Field(None, max_length=30)
    role: UserRole = UserRole.MEMBER
    status: UserStatus = UserStatus.ACTIVE


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    email: EmailStr | None = None
    mobile: str | None = Field(None, max_length=30)
    role: UserRole | None = None
    status: UserStatus | None = None
    password: str | None = Field(None, min_length=8, max_length=128)


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    items: list[UserRead]
    total: int
    page: int
    page_size: int


class CurrentUser(BaseModel):
    id: str
    organization_id: str
    name: str
    email: EmailStr
    mobile: str | None
    role: UserRole
    status: UserStatus


class MeResponse(BaseModel):
    user: UserRead
    organization: OrganizationSummary
