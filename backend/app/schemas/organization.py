from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationRead(OrganizationBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class OrganizationSummary(BaseModel):
    id: str
    name: str
