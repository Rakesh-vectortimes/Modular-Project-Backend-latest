from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SoftwareBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    category: str | None = Field(None, max_length=100)


class SoftwareCreate(SoftwareBase):
    pass


class SoftwareUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    category: str | None = Field(None, max_length=100)


class SoftwareRead(SoftwareBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    owner_id: str
    created_at: datetime
    updated_at: datetime
